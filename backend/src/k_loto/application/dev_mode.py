"""Idempotent local development fixtures using normal domain records."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.weekly import draw_configuration_snapshot
from k_loto.domain.enums import (
    DrawStatus,
    LedgerAccountKind,
    LotteryKind,
    TransactionType,
)
from k_loto.domain.schedules import next_draw_at, sales_close_at
from k_loto.infrastructure.database.models import (
    Balance,
    DistributionFund,
    Draw,
    JackpotAccount,
    KasperFundAccount,
    LedgerTransaction,
    Lottery,
    LotteryReserve,
)

KASPER_FUND_ID = UUID("4b415350-4552-4655-4e44-000000000001")


@dataclass(frozen=True, slots=True)
class DevBootstrapConfig:
    initial_user_balance: int
    weekly_ticket_price: int
    weekly_base_jackpot: int
    weekly_reserve: int


def _credit_entry(
    *,
    key: str,
    account_kind: LedgerAccountKind,
    account_id: UUID,
    amount: int,
    user_id: UUID | None = None,
    lottery_id: UUID | None = None,
) -> LedgerTransaction:
    return LedgerTransaction(
        id=uuid4(),
        operation_id=uuid4(),
        idempotency_key=key,
        account_kind=account_kind,
        account_id=account_id,
        type=TransactionType.SYSTEM_ADJUSTMENT,
        amount=amount,
        balance_before=0,
        balance_after=amount,
        user_id=user_id,
        lottery_id=lottery_id,
        details={"reason": "local development bootstrap"},
    )


class DevBootstrapService:
    """Create local-only playable fixtures without bypassing ledger rules."""

    def __init__(self, session: AsyncSession, config: DevBootstrapConfig) -> None:
        self._session = session
        self._config = config

    async def ensure(self, user_id: UUID, *, now: datetime) -> None:
        if self._config.weekly_ticket_price % 4:
            raise ValueError("Development Weekly price must be divisible by 4 CAS.")
        async with self._session.begin():
            await self._ensure_kasper_fund()
            await self._ensure_user_funding(user_id)
            await self._ensure_weekly(now)
            await self._ensure_daily(now)

    async def _ensure_kasper_fund(self) -> None:
        fund = await self._session.scalar(
            select(KasperFundAccount).where(KasperFundAccount.id == KASPER_FUND_ID)
        )
        if fund is not None:
            return
        amount = 1_000_000_000_000_000
        fund = KasperFundAccount(id=KASPER_FUND_ID, balance=amount, version=1)
        self._session.add(fund)
        self._session.add(
            _credit_entry(
                key="dev-bootstrap:kasper-fund",
                account_kind=LedgerAccountKind.KASPER_FUND,
                account_id=fund.id,
                amount=amount,
            )
        )

    async def refill_user(self, user_id: UUID, amount: int) -> int:
        if amount <= 0:
            raise ValueError("Local development refill must be positive.")
        async with self._session.begin():
            balance = await self._session.scalar(
                select(Balance).where(Balance.user_id == user_id).with_for_update()
            )
            if balance is None:
                raise RuntimeError("Local development user balance is missing.")
            before = balance.amount
            balance.amount += amount
            balance.version += 1
            self._session.add(
                LedgerTransaction(
                    id=uuid4(),
                    operation_id=uuid4(),
                    idempotency_key=f"dev-refill:user:{user_id}:{uuid4()}",
                    account_kind=LedgerAccountKind.USER_BALANCE,
                    account_id=user_id,
                    type=TransactionType.SYSTEM_ADJUSTMENT,
                    amount=amount,
                    balance_before=before,
                    balance_after=balance.amount,
                    user_id=user_id,
                    details={"reason": "local development refill"},
                )
            )
        return balance.amount

    async def _ensure_user_funding(self, user_id: UUID) -> None:
        balance = await self._session.scalar(
            select(Balance).where(Balance.user_id == user_id).with_for_update()
        )
        if balance is None:
            raise RuntimeError("Local development user balance is missing.")
        key = f"dev-bootstrap:user:{user_id}:initial"
        existing = await self._session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.idempotency_key == key)
        )
        if existing is not None or self._config.initial_user_balance == 0:
            return
        before = balance.amount
        balance.amount += self._config.initial_user_balance
        balance.version += 1
        self._session.add(
            LedgerTransaction(
                id=uuid4(),
                operation_id=uuid4(),
                idempotency_key=key,
                account_kind=LedgerAccountKind.USER_BALANCE,
                account_id=user_id,
                type=TransactionType.SYSTEM_ADJUSTMENT,
                amount=self._config.initial_user_balance,
                balance_before=before,
                balance_after=balance.amount,
                user_id=user_id,
                details={"reason": "local development bootstrap"},
            )
        )

    async def _ensure_weekly(self, now: datetime) -> None:
        lottery = await self._session.scalar(
            select(Lottery).where(Lottery.code == "weekly").with_for_update()
        )
        created = lottery is None
        if lottery is None:
            lottery = Lottery(
                id=uuid4(),
                code="weekly",
                name="Kasper Grand",
                kind=LotteryKind.WEEKLY,
                ruleset_code="weekly_grand_5_35_2_5",
                numbers_to_pick=7,
                max_number=40,
                ticket_price=self._config.weekly_ticket_price,
                timezone="Europe/Moscow",
                schedule={"weekday": "sunday", "draw_time": "20:00"},
                sales_cutoff_minutes=5,
                is_active=True,
                next_draw_number=1,
                next_ticket_number=1,
            )
            self._session.add(lottery)
        jackpot = await self._ensure_weekly_accounts(lottery, created=created)
        await self._ensure_draw(lottery, now, jackpot)

    async def _ensure_weekly_accounts(
        self, lottery: Lottery, *, created: bool
    ) -> JackpotAccount:
        jackpot = None
        distribution = None
        reserve = None
        if not created:
            jackpot = await self._session.scalar(
                select(JackpotAccount)
                .where(JackpotAccount.lottery_id == lottery.id)
                .with_for_update()
            )
            distribution = await self._session.scalar(
                select(DistributionFund)
                .where(DistributionFund.lottery_id == lottery.id)
                .with_for_update()
            )
            reserve = await self._session.scalar(
                select(LotteryReserve)
                .where(LotteryReserve.lottery_id == lottery.id)
                .with_for_update()
            )
        if jackpot is None:
            jackpot = JackpotAccount(
                id=uuid4(),
                lottery_id=lottery.id,
                balance=self._config.weekly_base_jackpot,
                base_amount=self._config.weekly_base_jackpot,
                version=1,
            )
            self._session.add(jackpot)
            if jackpot.balance:
                self._session.add(
                    _credit_entry(
                        key=f"dev-bootstrap:lottery:{lottery.id}:jackpot",
                        account_kind=LedgerAccountKind.JACKPOT,
                        account_id=jackpot.id,
                        amount=jackpot.balance,
                        lottery_id=lottery.id,
                    )
                )
        if distribution is None:
            self._session.add(
                DistributionFund(
                    id=uuid4(), lottery_id=lottery.id, balance=0, version=1
                )
            )
        if reserve is None:
            reserve = LotteryReserve(
                id=uuid4(),
                lottery_id=lottery.id,
                balance=self._config.weekly_reserve,
                version=1,
            )
            self._session.add(reserve)
            if reserve.balance:
                self._session.add(
                    _credit_entry(
                        key=f"dev-bootstrap:lottery:{lottery.id}:reserve",
                        account_kind=LedgerAccountKind.LOTTERY_RESERVE,
                        account_id=reserve.id,
                        amount=reserve.balance,
                        lottery_id=lottery.id,
                    )
                )
        return jackpot

    async def _ensure_daily(self, now: datetime) -> None:
        for code, name, slots in (
            ("pll", "ПЛЛ-лото", ["02:22", "13:45"]),
            ("pss", "ПСС-Лото", ["12:00", "20:30"]),
            ("khan", "ХАН-Лото", ["09:00", "18:00"]),
        ):
            lottery = await self._session.scalar(
                select(Lottery).where(Lottery.code == code).with_for_update()
            )
            created = lottery is None
            if lottery is None:
                lottery = Lottery(
                    id=uuid4(),
                    code=code,
                    name=name,
                    kind=LotteryKind.DAILY,
                    ruleset_code="daily_4_15",
                    numbers_to_pick=4,
                    max_number=15,
                    ticket_price=self._config.weekly_ticket_price,
                    timezone="Europe/Moscow",
                    schedule={"slots": slots},
                    sales_cutoff_minutes=2,
                    is_active=True,
                    next_draw_number=1,
                    next_ticket_number=1,
                )
                self._session.add(lottery)
            jackpot = await self._ensure_weekly_accounts(lottery, created=created)
            await self._ensure_draw(lottery, now, jackpot)

    async def _ensure_draw(
        self, lottery: Lottery, now: datetime, jackpot: JackpotAccount
    ) -> None:
        open_draw = await self._session.scalar(
            select(Draw)
            .where(
                Draw.lottery_id == lottery.id,
                Draw.status == DrawStatus.SCHEDULED,
                Draw.sales_close_at > now,
            )
            .order_by(Draw.scheduled_at)
            .limit(1)
        )
        if open_draw is not None:
            return
        latest = await self._session.scalar(
            select(Draw)
            .where(Draw.lottery_id == lottery.id)
            .order_by(Draw.scheduled_at.desc())
            .limit(1)
        )
        scheduled_at = next_draw_at(
            lottery.kind,
            latest.scheduled_at if latest is not None else now,
            lottery.schedule,
        )
        self._session.add(
            Draw(
                id=uuid4(),
                lottery_id=lottery.id,
                public_number=lottery.next_draw_number,
                status=DrawStatus.SCHEDULED,
                scheduled_at=scheduled_at,
                sales_close_at=sales_close_at(
                    lottery.kind,
                    scheduled_at,
                    lottery.sales_cutoff_minutes,
                    lottery.schedule,
                ),
                correlation_id=uuid4(),
                ticket_count=0,
                total_sales=0,
                total_payout=0,
                reserve_used=0,
                kasper_fund_used=0,
                configuration_snapshot=draw_configuration_snapshot(
                    lottery, jackpot.base_amount
                ),
            )
        )
        lottery.next_draw_number += 1
