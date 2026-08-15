"""Administrator read models and audited mutation use cases."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4, uuid5

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.enums import (
    AuditAction,
    DrawStatus,
    LedgerAccountKind,
    LotteryKind,
    TransactionType,
)
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    Balance,
    DistributionFund,
    Draw,
    JackpotAccount,
    LedgerTransaction,
    Lottery,
    LotteryReserve,
    Ticket,
    User,
)

ADMIN_NAMESPACE = UUID("8c48cd74-45ee-46eb-bf5b-e11944f87e3d")


@dataclass(frozen=True, slots=True)
class AdjustmentResult:
    amount: int
    already_processed: bool


@dataclass(frozen=True, slots=True)
class AdminPlayer:
    id: UUID
    display_name: str
    username: str | None
    telegram_id: int | None
    is_active: bool
    balance: int
    ticket_count: int
    spent: int
    won: int
    net: int


@dataclass(frozen=True, slots=True)
class AdminLottery:
    id: UUID
    code: str
    name: str
    kind: LotteryKind
    ticket_price: int | None
    base_jackpot: int
    current_jackpot: int
    distribution_fund: int
    reserve: int
    schedule: dict[str, Any]
    sales_cutoff_minutes: int | None
    is_active: bool
    next_draw_number: int | None
    next_draw_at: datetime | None


@dataclass(frozen=True, slots=True)
class AdminTransaction:
    id: UUID
    operation_id: UUID
    type: TransactionType
    account_kind: LedgerAccountKind
    amount: int
    balance_before: int
    balance_after: int
    user_id: UUID | None
    lottery_id: UUID | None
    draw_id: UUID | None
    ticket_id: UUID | None
    created_at: datetime
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AdminDraw:
    id: UUID
    lottery_id: UUID
    lottery_code: str
    public_number: int
    status: DrawStatus
    scheduled_at: datetime
    sales_close_at: datetime
    executed_at: datetime | None
    winning_numbers: tuple[int, ...] | None
    ticket_count: int
    total_sales: int
    total_payout: int
    jackpot_opening: int | None
    jackpot_closing: int | None
    distribution_opening: int | None
    distribution_closing: int | None
    reserve_used: int
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class AdminDrawTicket:
    id: UUID
    public_number: int
    user_id: UUID
    numbers: tuple[int, ...]
    purchase_price: int
    matches: int | None
    prize_amount: int


@dataclass(frozen=True, slots=True)
class NumberStatistic:
    number: int
    appearances: int
    draw_percentage: float
    last_appearance: datetime | None
    draws_since_last: int | None


@dataclass(frozen=True, slots=True)
class AdminAuditEntry:
    id: UUID
    admin_user_id: UUID
    action: AuditAction
    entity_type: str
    entity_id: UUID | None
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    reason: str | None
    created_at: datetime


async def ensure_admin_user(session: AsyncSession, username: str) -> UUID:
    """Bind an environment credential to a stable database audit identity."""
    admin_id = uuid5(ADMIN_NAMESPACE, username.casefold())
    async with session.begin():
        await session.execute(
            insert(User)
            .values(
                id=admin_id,
                telegram_id=None,
                username=username,
                display_name="K-Loto Administrator",
                is_active=True,
                is_admin=True,
            )
            .on_conflict_do_update(
                index_elements=[User.id],
                set_={"username": username, "is_active": True, "is_admin": True},
            )
        )
    return admin_id


class AdminMutationService:
    """Perform administrator changes under locks with ledger and audit records."""

    def __init__(self, session: AsyncSession, admin_user_id: UUID) -> None:
        self._session = session
        self._admin_user_id = admin_user_id

    async def set_user_balance(
        self,
        user_id: UUID,
        *,
        target_amount: int,
        reason: str,
        idempotency_key: str,
    ) -> AdjustmentResult:
        _validate_adjustment(target_amount, reason, idempotency_key)
        ledger_key = f"admin-balance:{idempotency_key}"
        async with self._session.begin():
            existing = await self._session.scalar(
                select(LedgerTransaction).where(
                    LedgerTransaction.idempotency_key == ledger_key
                )
            )
            if existing is not None:
                return AdjustmentResult(existing.balance_after, True)
            balance = await self._session.scalar(
                select(Balance).where(Balance.user_id == user_id).with_for_update()
            )
            if balance is None:
                raise LookupError("Player balance does not exist.")
            before = balance.amount
            if before == target_amount:
                return AdjustmentResult(before, False)
            balance.amount = target_amount
            balance.version += 1
            operation_id = uuid4()
            self._session.add(
                LedgerTransaction(
                    id=uuid4(),
                    operation_id=operation_id,
                    idempotency_key=ledger_key,
                    account_kind=LedgerAccountKind.USER_BALANCE,
                    account_id=user_id,
                    type=TransactionType.ADMIN_BALANCE_ADJUSTMENT,
                    amount=target_amount - before,
                    balance_before=before,
                    balance_after=target_amount,
                    user_id=user_id,
                    details={
                        "reason": reason,
                        "admin_user_id": str(self._admin_user_id),
                    },
                )
            )
            self._audit(
                AuditAction.ADJUST,
                "user_balance",
                user_id,
                {"amount": before},
                {"amount": target_amount},
                reason,
            )
        return AdjustmentResult(target_amount, False)

    async def set_reserve(
        self,
        lottery_id: UUID,
        *,
        target_amount: int,
        reason: str,
        idempotency_key: str,
    ) -> AdjustmentResult:
        _validate_adjustment(target_amount, reason, idempotency_key)
        ledger_key = f"admin-reserve:{idempotency_key}"
        async with self._session.begin():
            existing = await self._session.scalar(
                select(LedgerTransaction).where(
                    LedgerTransaction.idempotency_key == ledger_key
                )
            )
            if existing is not None:
                return AdjustmentResult(existing.balance_after, True)
            reserve = await self._session.scalar(
                select(LotteryReserve)
                .where(LotteryReserve.lottery_id == lottery_id)
                .with_for_update()
            )
            if reserve is None:
                raise LookupError("Lottery reserve does not exist.")
            before = reserve.balance
            if before == target_amount:
                return AdjustmentResult(before, False)
            reserve.balance = target_amount
            reserve.version += 1
            self._session.add(
                LedgerTransaction(
                    id=uuid4(),
                    operation_id=uuid4(),
                    idempotency_key=ledger_key,
                    account_kind=LedgerAccountKind.LOTTERY_RESERVE,
                    account_id=reserve.id,
                    type=TransactionType.RESERVE_ADJUSTMENT,
                    amount=target_amount - before,
                    balance_before=before,
                    balance_after=target_amount,
                    lottery_id=lottery_id,
                    details={
                        "reason": reason,
                        "admin_user_id": str(self._admin_user_id),
                    },
                )
            )
            self._audit(
                AuditAction.ADJUST,
                "lottery_reserve",
                reserve.id,
                {"amount": before},
                {"amount": target_amount},
                reason,
            )
        return AdjustmentResult(target_amount, False)

    async def configure_lottery(
        self,
        lottery_id: UUID,
        *,
        ticket_price: int,
        base_jackpot: int,
        reason: str,
    ) -> AdminLottery:
        if ticket_price <= 0 or base_jackpot < 0:
            raise ValueError("Lottery CAS values are outside their valid range.")
        if not reason.strip() or len(reason) > 512:
            raise ValueError("A reason of 1 to 512 characters is required.")
        async with self._session.begin():
            lottery = await self._session.scalar(
                select(Lottery).where(Lottery.id == lottery_id).with_for_update()
            )
            jackpot = await self._session.scalar(
                select(JackpotAccount)
                .where(JackpotAccount.lottery_id == lottery_id)
                .with_for_update()
            )
            if lottery is None or jackpot is None:
                raise LookupError("Lottery or jackpot account does not exist.")
            if lottery.kind == LotteryKind.WEEKLY and ticket_price % 4:
                raise ValueError("Weekly ticket price must be divisible by 4 CAS.")
            old_values = {
                "ticket_price": lottery.ticket_price,
                "base_jackpot": jackpot.base_amount,
            }
            lottery.ticket_price = ticket_price
            jackpot.base_amount = base_jackpot
            jackpot.version += 1
            self._audit(
                AuditAction.UPDATE,
                "lottery_configuration",
                lottery.id,
                old_values,
                {"ticket_price": ticket_price, "base_jackpot": base_jackpot},
                reason,
            )
        return await AdminQueryService(self._session).lottery(lottery_id)

    def _audit(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: UUID | None,
        old_values: dict[str, Any] | None,
        new_values: dict[str, Any] | None,
        reason: str,
    ) -> None:
        self._session.add(
            AdminAuditLog(
                id=uuid4(),
                admin_user_id=self._admin_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                old_values=old_values,
                new_values=new_values,
                reason=reason.strip(),
            )
        )


def _validate_adjustment(target: int, reason: str, key: str) -> None:
    if target < 0:
        raise ValueError("CAS balance cannot be negative.")
    if not reason.strip() or len(reason) > 512:
        raise ValueError("A reason of 1 to 512 characters is required.")
    if not key or len(key) > 100:
        raise ValueError("Idempotency key must contain 1 to 100 characters.")


class AdminQueryService:
    """Read immutable business history and current operational projections."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def players(self) -> tuple[AdminPlayer, ...]:
        rows = (
            await self._session.execute(
                select(User, Balance.amount, func.count(Ticket.id))
                .outerjoin(Balance, Balance.user_id == User.id)
                .outerjoin(Ticket, Ticket.user_id == User.id)
                .where(User.is_admin.is_(False))
                .group_by(User.id, Balance.amount)
                .order_by(User.created_at.desc())
            )
        ).all()
        return tuple(
            [
                await self._player(user, balance or 0, ticket_count or 0)
                for user, balance, ticket_count in rows
            ]
        )

    async def player(self, user_id: UUID) -> AdminPlayer:
        row = (
            await self._session.execute(
                select(User, Balance.amount, func.count(Ticket.id))
                .outerjoin(Balance, Balance.user_id == User.id)
                .outerjoin(Ticket, Ticket.user_id == User.id)
                .where(User.id == user_id, User.is_admin.is_(False))
                .group_by(User.id, Balance.amount)
            )
        ).one_or_none()
        if row is None:
            raise LookupError("Player does not exist.")
        user, balance, ticket_count = row
        return await self._player(user, balance or 0, ticket_count or 0)

    async def _player(self, user: User, balance: int, ticket_count: int) -> AdminPlayer:
        ledger = (
            await self._session.scalars(
                select(LedgerTransaction).where(
                    LedgerTransaction.user_id == user.id,
                    LedgerTransaction.account_kind == LedgerAccountKind.USER_BALANCE,
                )
            )
        ).all()
        spent = -sum(
            item.amount
            for item in ledger
            if item.type == TransactionType.TICKET_PURCHASE and item.amount < 0
        )
        won = sum(
            item.amount
            for item in ledger
            if item.type
            in {TransactionType.PRIZE_PAYOUT, TransactionType.JACKPOT_PAYOUT}
            and item.amount > 0
        )
        return AdminPlayer(
            user.id,
            user.display_name,
            user.username,
            user.telegram_id,
            user.is_active,
            balance,
            ticket_count,
            spent,
            won,
            won - spent,
        )

    async def lotteries(self) -> tuple[AdminLottery, ...]:
        ids = (
            await self._session.scalars(select(Lottery.id).order_by(Lottery.code))
        ).all()
        return tuple([await self.lottery(lottery_id) for lottery_id in ids])

    async def lottery(self, lottery_id: UUID) -> AdminLottery:
        row = (
            await self._session.execute(
                select(
                    Lottery,
                    JackpotAccount,
                    DistributionFund,
                    LotteryReserve,
                )
                .outerjoin(JackpotAccount, JackpotAccount.lottery_id == Lottery.id)
                .outerjoin(DistributionFund, DistributionFund.lottery_id == Lottery.id)
                .outerjoin(LotteryReserve, LotteryReserve.lottery_id == Lottery.id)
                .where(Lottery.id == lottery_id)
            )
        ).one_or_none()
        if row is None:
            raise LookupError("Lottery does not exist.")
        lottery, jackpot, distribution, reserve = row
        next_draw = await self._session.scalar(
            select(Draw)
            .where(
                Draw.lottery_id == lottery.id,
                Draw.status == DrawStatus.SCHEDULED,
            )
            .order_by(Draw.scheduled_at)
            .limit(1)
        )
        return AdminLottery(
            lottery.id,
            lottery.code,
            lottery.name,
            lottery.kind,
            lottery.ticket_price,
            jackpot.base_amount if jackpot else 0,
            jackpot.balance if jackpot else 0,
            distribution.balance if distribution else 0,
            reserve.balance if reserve else 0,
            lottery.schedule,
            lottery.sales_cutoff_minutes,
            lottery.is_active,
            next_draw.public_number if next_draw else None,
            next_draw.scheduled_at if next_draw else None,
        )

    async def transactions(
        self,
        *,
        transaction_type: TransactionType | None = None,
        user_id: UUID | None = None,
        lottery_id: UUID | None = None,
        draw_id: UUID | None = None,
        ticket_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[AdminTransaction, ...]:
        statement = select(LedgerTransaction)
        filters = [
            (LedgerTransaction.type == transaction_type)
            if transaction_type is not None
            else None,
            (LedgerTransaction.user_id == user_id) if user_id else None,
            (LedgerTransaction.lottery_id == lottery_id) if lottery_id else None,
            (LedgerTransaction.draw_id == draw_id) if draw_id else None,
            (LedgerTransaction.ticket_id == ticket_id) if ticket_id else None,
            (LedgerTransaction.created_at >= date_from) if date_from else None,
            (LedgerTransaction.created_at <= date_to) if date_to else None,
        ]
        statement = statement.where(*(item for item in filters if item is not None))
        rows = (
            await self._session.scalars(
                statement.order_by(LedgerTransaction.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return tuple(
            AdminTransaction(
                item.id,
                item.operation_id,
                item.type,
                item.account_kind,
                item.amount,
                item.balance_before,
                item.balance_after,
                item.user_id,
                item.lottery_id,
                item.draw_id,
                item.ticket_id,
                item.created_at,
                item.details,
            )
            for item in rows
        )

    async def draws(
        self,
        *,
        lottery_id: UUID | None = None,
        status: DrawStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[AdminDraw, ...]:
        statement = select(Draw, Lottery.code).join(
            Lottery, Lottery.id == Draw.lottery_id
        )
        if lottery_id:
            statement = statement.where(Draw.lottery_id == lottery_id)
        if status:
            statement = statement.where(Draw.status == status)
        rows = (
            await self._session.execute(
                statement.order_by(Draw.scheduled_at.desc()).limit(limit).offset(offset)
            )
        ).all()
        return tuple(self._draw(draw, code) for draw, code in rows)

    async def draw(
        self, draw_id: UUID
    ) -> tuple[AdminDraw, tuple[AdminDrawTicket, ...]]:
        row = (
            await self._session.execute(
                select(Draw, Lottery.code)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .where(Draw.id == draw_id)
            )
        ).one_or_none()
        if row is None:
            raise LookupError("Draw does not exist.")
        draw, code = row
        tickets = (
            await self._session.scalars(
                select(Ticket)
                .where(Ticket.draw_id == draw_id)
                .order_by(Ticket.public_number)
            )
        ).all()
        return self._draw(draw, code), tuple(
            AdminDrawTicket(
                ticket.id,
                ticket.public_number,
                ticket.user_id,
                tuple(ticket.numbers),
                ticket.purchase_price,
                ticket.matches,
                ticket.prize_amount,
            )
            for ticket in tickets
        )

    @staticmethod
    def _draw(draw: Draw, lottery_code: str) -> AdminDraw:
        return AdminDraw(
            draw.id,
            draw.lottery_id,
            lottery_code,
            draw.public_number,
            draw.status,
            draw.scheduled_at,
            draw.sales_close_at,
            draw.executed_at,
            tuple(draw.winning_numbers) if draw.winning_numbers else None,
            draw.ticket_count,
            draw.total_sales,
            draw.total_payout,
            draw.jackpot_opening,
            draw.jackpot_closing,
            draw.distribution_opening,
            draw.distribution_closing,
            draw.reserve_used,
            draw.correlation_id,
        )

    async def number_statistics(self, lottery_id: UUID) -> tuple[NumberStatistic, ...]:
        lottery = await self._session.scalar(
            select(Lottery).where(Lottery.id == lottery_id)
        )
        if lottery is None:
            raise LookupError("Lottery does not exist.")
        draws = (
            await self._session.scalars(
                select(Draw)
                .where(
                    Draw.lottery_id == lottery_id,
                    Draw.status == DrawStatus.COMPLETED,
                    Draw.winning_numbers.is_not(None),
                )
                .order_by(Draw.scheduled_at)
            )
        ).all()
        positions: dict[int, list[int]] = {
            number: [] for number in range(1, lottery.max_number + 1)
        }
        for index, draw in enumerate(draws):
            for number in draw.winning_numbers or []:
                positions[number].append(index)
        total = len(draws)
        return tuple(
            NumberStatistic(
                number,
                len(indexes),
                round((len(indexes) / total) * 100, 2) if total else 0.0,
                draws[indexes[-1]].scheduled_at if indexes else None,
                (total - 1 - indexes[-1]) if indexes else None,
            )
            for number, indexes in positions.items()
        )

    async def audit(self, *, limit: int = 100) -> tuple[AdminAuditEntry, ...]:
        rows = (
            await self._session.scalars(
                select(AdminAuditLog)
                .order_by(AdminAuditLog.created_at.desc())
                .limit(limit)
            )
        ).all()
        return tuple(
            AdminAuditEntry(
                item.id,
                item.admin_user_id,
                item.action,
                item.entity_type,
                item.entity_id,
                item.old_values,
                item.new_values,
                item.reason,
                item.created_at,
            )
            for item in rows
        )

    async def dashboard_counts(self) -> dict[str, int]:
        users = await self._session.scalar(
            select(func.count(User.id)).where(User.is_admin.is_(False))
        )
        tickets = await self._session.scalar(select(func.count(Ticket.id)))
        completed = await self._session.scalar(
            select(func.count(Draw.id)).where(Draw.status == DrawStatus.COMPLETED)
        )
        pending = await self._session.scalar(
            select(func.count(Draw.id)).where(
                or_(
                    Draw.status == DrawStatus.SCHEDULED,
                    Draw.status == DrawStatus.CLOSED,
                    Draw.status == DrawStatus.DRAWING,
                    Draw.status == DrawStatus.SETTLING,
                    Draw.status == DrawStatus.FAILED,
                )
            )
        )
        return {
            "users": users or 0,
            "tickets": tickets or 0,
            "completed_draws": completed or 0,
            "pending_draws": pending or 0,
        }
