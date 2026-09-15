"""Administrator read models and audited mutation use cases."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4, uuid5

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.query_scope import LotteryScope, lottery_scope
from k_loto.domain.enums import (
    AuditAction,
    DrawStatus,
    LedgerAccountKind,
    LotteryKind,
    NotificationStatus,
    NotificationType,
    TicketStatus,
    TransactionType,
)
from k_loto.domain.lotteries import MOSCOW, draw_display_name, is_fast_lottery
from k_loto.domain.lottery_rules import get_lottery_rules
from k_loto.domain.schedules import next_draw_at
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    AutoPlaySetting,
    Balance,
    DistributionFund,
    Draw,
    JackpotAccount,
    JackpotWinEvent,
    KasperFundAccount,
    LedgerTransaction,
    Lottery,
    LotteryReserve,
    NotificationOutbox,
    SchedulerHeartbeat,
    Ticket,
    User,
    UserNotificationPreference,
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
    active_ticket_count: int
    spent: int
    won: int
    net: int
    telegram_notifications_enabled: bool
    auto_play_enabled: bool
    auto_play_tickets_per_draw: int
    auto_play_last_attempted_at: datetime | None
    auto_play_last_succeeded_at: datetime | None
    auto_play_last_error: str | None


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
    max_tickets_per_purchase: int
    max_tickets_per_user_per_draw: int
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
    lottery_name: str
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
    kasper_fund_used: int
    correlation_id: UUID
    jackpot_amount: int | None = None


@dataclass(frozen=True, slots=True)
class AdminScheduleEntry:
    id: UUID
    lottery_id: UUID
    lottery_name: str
    public_number: int
    scheduled_at: datetime


@dataclass(frozen=True, slots=True)
class AdminDrawTicket:
    id: UUID
    public_number: int
    user_id: UUID
    numbers: tuple[int, ...]
    purchase_price: int
    matches: int | None
    prize_amount: int
    bingo_result: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class NumberStatistic:
    number: int
    appearances: int
    draw_percentage: float
    last_appearance: datetime | None
    draws_since_last: int | None


@dataclass(frozen=True, slots=True)
class NumberStatisticsReport:
    lottery_id: UUID
    lottery_name: str
    period_start: datetime | None
    window_size: int | None
    draw_count: int
    first_draw_at: datetime | None
    last_draw_at: datetime | None
    numbers: tuple[NumberStatistic, ...]


@dataclass(frozen=True, slots=True)
class TicketAnalyticsRow:
    lottery_id: UUID | None
    lottery_name: str
    is_active: bool | None
    total_tickets: int
    active_tickets: int
    settled_tickets: int
    winning_tickets: int
    participants: int
    winning_players: int
    total_sales: int
    total_payout: int


@dataclass(frozen=True, slots=True)
class TicketAnalytics:
    overall: TicketAnalyticsRow
    lotteries: tuple[TicketAnalyticsRow, ...]


@dataclass(frozen=True, slots=True)
class AdminActivityPoint:
    bucket_at: datetime
    ticket_count: int
    total_sales: int
    total_payout: int


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


@dataclass(frozen=True, slots=True)
class AdminNotification:
    id: UUID
    event_key: str
    user_id: UUID
    type: NotificationType
    status: NotificationStatus
    attempts: int
    available_at: datetime
    sent_at: datetime | None
    last_error: str | None
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
            ),
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

    async def set_jackpot(
        self,
        lottery_id: UUID,
        *,
        target_amount: int,
        reason: str,
        idempotency_key: str,
    ) -> AdjustmentResult:
        """Set a current jackpot through an immutable ledger adjustment."""
        _validate_adjustment(target_amount, reason, idempotency_key)
        ledger_key = f"admin-jackpot:{idempotency_key}"
        async with self._session.begin():
            existing = await self._session.scalar(
                select(LedgerTransaction).where(
                    LedgerTransaction.idempotency_key == ledger_key
                )
            )
            if existing is not None:
                return AdjustmentResult(existing.balance_after, True)
            jackpot = await self._session.scalar(
                select(JackpotAccount)
                .where(JackpotAccount.lottery_id == lottery_id)
                .with_for_update()
            )
            if jackpot is None:
                raise LookupError("Lottery jackpot does not exist.")
            before = jackpot.balance
            if before == target_amount:
                return AdjustmentResult(before, False)
            jackpot.balance = target_amount
            jackpot.version += 1
            self._session.add(
                LedgerTransaction(
                    id=uuid4(),
                    operation_id=uuid4(),
                    idempotency_key=ledger_key,
                    account_kind=LedgerAccountKind.JACKPOT,
                    account_id=jackpot.id,
                    type=TransactionType.SYSTEM_ADJUSTMENT,
                    amount=target_amount - before,
                    balance_before=before,
                    balance_after=target_amount,
                    lottery_id=lottery_id,
                    details={
                        "reason": reason,
                        "source": "admin",
                        "admin_user_id": str(self._admin_user_id),
                    },
                )
            )
            self._audit(
                AuditAction.ADJUST,
                "jackpot_account",
                jackpot.id,
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
        sales_cutoff_minutes: int | None = None,
        max_tickets_per_purchase: int | None = None,
        max_tickets_per_user_per_draw: int | None = None,
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
            rules = get_lottery_rules(lottery.ruleset_code)
            if ticket_price % rules.price_divisor:
                raise ValueError(
                    f"Ticket price must be divisible by {rules.price_divisor} CAS."
                )
            old_values = {
                "ticket_price": lottery.ticket_price,
                "base_jackpot": jackpot.base_amount,
                "sales_cutoff_minutes": lottery.sales_cutoff_minutes,
                "max_tickets_per_purchase": lottery.max_tickets_per_purchase,
                "max_tickets_per_user_per_draw": (
                    lottery.max_tickets_per_user_per_draw
                ),
            }
            next_purchase_limit = (
                max_tickets_per_purchase
                if max_tickets_per_purchase is not None
                else (lottery.max_tickets_per_purchase or 1000)
            )
            next_player_limit = (
                max_tickets_per_user_per_draw
                if max_tickets_per_user_per_draw is not None
                else (lottery.max_tickets_per_user_per_draw or 5000)
            )
            if not 1 <= next_purchase_limit <= 1000:
                raise ValueError("Purchase limit must be between 1 and 1000.")
            if not next_purchase_limit <= next_player_limit <= 100_000:
                raise ValueError("Player draw limit is outside its valid range.")
            if (
                sales_cutoff_minutes is not None
                and not 0 <= sales_cutoff_minutes <= 1440
            ):
                raise ValueError("Sales cutoff is outside its valid range.")
            initialize_jackpot = (
                jackpot.balance == 0 and jackpot.base_amount == 0 and base_jackpot > 0
            )
            lottery.ticket_price = ticket_price
            if sales_cutoff_minutes is not None:
                lottery.sales_cutoff_minutes = sales_cutoff_minutes
            lottery.max_tickets_per_purchase = next_purchase_limit
            lottery.max_tickets_per_user_per_draw = next_player_limit
            jackpot.base_amount = base_jackpot
            jackpot.version += 1
            if initialize_jackpot:
                jackpot.balance = base_jackpot
                operation_id = uuid4()
                self._session.add(
                    LedgerTransaction(
                        id=uuid4(),
                        operation_id=operation_id,
                        idempotency_key=(
                            f"admin-jackpot-initialize:{lottery.id}:{base_jackpot}"
                        ),
                        account_kind=LedgerAccountKind.JACKPOT,
                        account_id=jackpot.id,
                        type=TransactionType.SYSTEM_ADJUSTMENT,
                        amount=base_jackpot,
                        balance_before=0,
                        balance_after=base_jackpot,
                        lottery_id=lottery.id,
                        details={
                            "reason": reason,
                            "admin_user_id": str(self._admin_user_id),
                        },
                    )
                )
            self._audit(
                AuditAction.UPDATE,
                "lottery_configuration",
                lottery.id,
                old_values,
                {
                    "ticket_price": ticket_price,
                    "base_jackpot": base_jackpot,
                    "sales_cutoff_minutes": lottery.sales_cutoff_minutes,
                    "max_tickets_per_purchase": next_purchase_limit,
                    "max_tickets_per_user_per_draw": next_player_limit,
                },
                reason,
            )
        return await AdminQueryService(self._session).lottery(lottery_id)

    async def set_auto_play(
        self,
        user_id: UUID,
        *,
        enabled: bool,
        tickets_per_draw: int,
        reason: str,
    ) -> AutoPlaySetting:
        if not 1 <= tickets_per_draw <= 5:
            raise ValueError("Auto-play ticket count must be between 1 and 5.")
        if not reason.strip() or len(reason) > 512:
            raise ValueError("A reason of 1 to 512 characters is required.")
        async with self._session.begin():
            user = await self._session.scalar(
                select(User)
                .where(User.id == user_id, User.is_admin.is_(False))
                .with_for_update()
            )
            if user is None:
                raise LookupError("Player does not exist.")
            setting = await self._session.get(
                AutoPlaySetting, user_id, with_for_update=True
            )
            old_values = (
                {
                    "enabled": setting.enabled,
                    "tickets_per_draw": setting.tickets_per_draw,
                }
                if setting
                else None
            )
            if setting is None:
                setting = AutoPlaySetting(
                    user_id=user_id,
                    enabled=enabled,
                    tickets_per_draw=tickets_per_draw,
                )
                self._session.add(setting)
            else:
                setting.enabled = enabled
                setting.tickets_per_draw = tickets_per_draw
                setting.last_error = None
            self._audit(
                AuditAction.UPDATE,
                "auto_play_setting",
                user_id,
                old_values,
                {"enabled": enabled, "tickets_per_draw": tickets_per_draw},
                reason,
            )
        return setting

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

    def __init__(self, session: AsyncSession, *, scope: LotteryScope = "all") -> None:
        self._session = session
        self._scope = scope

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
        active_ticket_count = int(
            await self._session.scalar(
                select(func.count(Ticket.id)).where(
                    Ticket.user_id == user.id,
                    Ticket.status == TicketStatus.PURCHASED,
                )
            )
            or 0
        )
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
        preference = await self._session.get(UserNotificationPreference, user.id)
        auto_play = await self._session.get(AutoPlaySetting, user.id)
        return AdminPlayer(
            user.id,
            user.display_name,
            user.username,
            user.telegram_id,
            user.is_active,
            balance,
            ticket_count,
            active_ticket_count,
            spent,
            won,
            won - spent,
            bool(preference and preference.telegram_enabled),
            bool(auto_play and auto_play.enabled),
            auto_play.tickets_per_draw if auto_play else 5,
            auto_play.last_attempted_at if auto_play else None,
            auto_play.last_succeeded_at if auto_play else None,
            auto_play.last_error if auto_play else None,
        )

    async def lotteries(self) -> tuple[AdminLottery, ...]:
        ids = (
            await self._session.scalars(
                select(Lottery.id)
                .where(lottery_scope(self._scope))
                .order_by(Lottery.code)
            )
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
            lottery.max_tickets_per_purchase,
            lottery.max_tickets_per_user_per_draw,
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
        period: str | None = None,
    ) -> tuple[AdminDraw, ...]:
        statement = (
            select(Draw, Lottery)
            .join(Lottery, Lottery.id == Draw.lottery_id)
            .where(lottery_scope(self._scope))
        )
        now = datetime.now(UTC)
        if period == "today":
            start = datetime.combine(
                now.astimezone(MOSCOW).date(), datetime.min.time(), tzinfo=MOSCOW
            ).astimezone(UTC)
            statement = statement.where(
                Draw.scheduled_at >= start,
                Draw.scheduled_at < start + timedelta(days=1),
            )
        elif period == "future":
            statement = statement.where(
                Draw.scheduled_at > now, Draw.status != DrawStatus.COMPLETED
            )
        elif period == "completed":
            statement = statement.where(Draw.status == DrawStatus.COMPLETED)
        elif period == "failed":
            statement = statement.where(Draw.status == DrawStatus.FAILED)
        if lottery_id:
            statement = statement.where(Draw.lottery_id == lottery_id)
        if status:
            statement = statement.where(Draw.status == status)
        rows = (
            await self._session.execute(
                statement.order_by(Draw.scheduled_at.desc()).limit(limit).offset(offset)
            )
        ).all()
        return tuple(self._draw(draw, lottery) for draw, lottery in rows)

    async def daily_schedule(
        self,
        *,
        lottery_id: UUID | None = None,
        now: datetime | None = None,
    ) -> tuple[AdminScheduleEntry, ...]:
        """Return the Moscow calendar day's draws for the owner timetable."""
        timestamp = now or datetime.now(UTC)
        local_day = timestamp.astimezone(MOSCOW).date()
        local_start = datetime.combine(local_day, datetime.min.time(), tzinfo=MOSCOW)
        start = local_start.astimezone(UTC)
        end = (local_start + timedelta(days=1)).astimezone(UTC)
        statement = (
            select(Draw, Lottery)
            .join(Lottery, Lottery.id == Draw.lottery_id)
            .where(
                Lottery.is_active.is_(True),
                lottery_scope(self._scope),
                Draw.scheduled_at >= start,
                Draw.scheduled_at < end,
            )
        )
        if lottery_id is not None:
            statement = statement.where(Draw.lottery_id == lottery_id)
        rows = (
            await self._session.execute(statement.order_by(Draw.scheduled_at))
        ).all()
        entries = [
            AdminScheduleEntry(
                id=draw.id,
                lottery_id=lottery.id,
                lottery_name=draw_display_name(
                    lottery.code, lottery.name, draw.scheduled_at
                ),
                public_number=draw.public_number,
                scheduled_at=draw.scheduled_at,
            )
            for draw, lottery in rows
        ]

        # Fast lotteries keep only a few future rows in the database. Project the
        # rest of today's immutable sequence for the information board without
        # creating draws, tickets, notifications, or scheduler work.
        lotteries = {lottery.id: lottery for _, lottery in rows}
        for lottery in lotteries.values():
            if not is_fast_lottery(lottery.code):
                continue
            lottery_entries = [
                entry for entry in entries if entry.lottery_id == lottery.id
            ]
            if not lottery_entries:
                continue
            scheduled_at = max(entry.scheduled_at for entry in lottery_entries)
            public_number = lottery.next_draw_number
            while True:
                scheduled_at = next_draw_at(
                    lottery.kind, scheduled_at, lottery.schedule
                )
                if scheduled_at >= end:
                    break
                entries.append(
                    AdminScheduleEntry(
                        id=uuid5(
                            ADMIN_NAMESPACE,
                            f"schedule:{lottery.id}:{scheduled_at.isoformat()}",
                        ),
                        lottery_id=lottery.id,
                        lottery_name=lottery.name,
                        public_number=public_number,
                        scheduled_at=scheduled_at,
                    )
                )
                public_number += 1

        return tuple(sorted(entries, key=lambda item: item.scheduled_at))

    async def draw(
        self, draw_id: UUID
    ) -> tuple[AdminDraw, tuple[AdminDrawTicket, ...]]:
        row = (
            await self._session.execute(
                select(Draw, Lottery, JackpotWinEvent.jackpot_amount)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .outerjoin(JackpotWinEvent, JackpotWinEvent.draw_id == Draw.id)
                .where(Draw.id == draw_id)
            )
        ).one_or_none()
        if row is None:
            raise LookupError("Draw does not exist.")
        draw, lottery, jackpot_amount = row
        tickets = (
            await self._session.scalars(
                select(Ticket)
                .where(Ticket.draw_id == draw_id)
                .order_by(Ticket.public_number)
            )
        ).all()
        return self._draw(draw, lottery, jackpot_amount), tuple(
            AdminDrawTicket(
                ticket.id,
                ticket.public_number,
                ticket.user_id,
                tuple(ticket.numbers),
                ticket.purchase_price,
                ticket.matches,
                ticket.prize_amount,
                ticket.bingo_result,
            )
            for ticket in tickets
        )

    @staticmethod
    def _draw(
        draw: Draw, lottery: Lottery, jackpot_amount: int | None = None
    ) -> AdminDraw:
        return AdminDraw(
            draw.id,
            draw.lottery_id,
            lottery.code,
            draw_display_name(lottery.code, lottery.name, draw.scheduled_at),
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
            draw.kasper_fund_used,
            draw.correlation_id,
            jackpot_amount,
        )

    async def number_statistics(
        self,
        lottery_id: UUID,
        *,
        date_from: datetime | None = None,
        limit: int | None = 20,
    ) -> NumberStatisticsReport:
        lottery = await self._session.scalar(
            select(Lottery).where(Lottery.id == lottery_id)
        )
        if lottery is None:
            raise LookupError("Lottery does not exist.")
        statement = select(Draw).where(
            Draw.lottery_id == lottery_id,
            Draw.status == DrawStatus.COMPLETED,
            Draw.winning_numbers.is_not(None),
            Draw.configuration_snapshot["ruleset_code"].astext == lottery.ruleset_code,
        )
        if date_from is not None:
            statement = statement.where(Draw.scheduled_at >= date_from)
        statement = statement.order_by(Draw.scheduled_at.desc())
        if limit is not None:
            statement = statement.limit(limit)
        recent_draws = (await self._session.scalars(statement)).all()
        draws = sorted(recent_draws, key=lambda item: item.scheduled_at)
        positions: dict[int, list[int]] = {
            number: [] for number in range(1, lottery.max_number + 1)
        }
        for index, draw in enumerate(draws):
            for number in draw.winning_numbers or []:
                positions[number].append(index)
        total = len(draws)
        return NumberStatisticsReport(
            lottery.id,
            lottery.name,
            date_from,
            limit,
            total,
            draws[0].scheduled_at if draws else None,
            draws[-1].scheduled_at if draws else None,
            tuple(
                NumberStatistic(
                    number,
                    len(indexes),
                    round((len(indexes) / total) * 100, 2) if total else 0.0,
                    draws[indexes[-1]].scheduled_at if indexes else None,
                    (total - 1 - indexes[-1]) if indexes else None,
                )
                for number, indexes in positions.items()
            ),
        )

    async def ticket_analytics(self) -> TicketAnalytics:
        """Return compact ticket outcome aggregates without loading ticket rows."""

        metrics = (
            func.count(Ticket.id),
            func.count(Ticket.id).filter(Ticket.status == TicketStatus.PURCHASED),
            func.count(Ticket.id).filter(Ticket.status == TicketStatus.SETTLED),
            func.count(Ticket.id).filter(Ticket.prize_amount > 0),
            func.count(func.distinct(Ticket.user_id)),
            func.count(func.distinct(Ticket.user_id)).filter(Ticket.prize_amount > 0),
            func.coalesce(func.sum(Ticket.purchase_price), 0),
            func.coalesce(func.sum(Ticket.prize_amount), 0),
        )
        overall_values = (
            await self._session.execute(
                select(*metrics)
                .select_from(Ticket)
                .join(Lottery, Lottery.id == Ticket.lottery_id)
                .where(lottery_scope(self._scope))
            )
        ).all()[0]
        lottery_values = (
            await self._session.execute(
                select(Lottery.id, Lottery.name, Lottery.is_active, *metrics)
                .outerjoin(Ticket, Ticket.lottery_id == Lottery.id)
                .where(lottery_scope(self._scope))
                .group_by(Lottery.id, Lottery.name, Lottery.is_active)
                .order_by(Lottery.is_active.desc(), Lottery.name)
            )
        ).all()

        def row(
            values: Any,
            *,
            lottery_id: UUID | None,
            name: str,
            active: bool | None,
            offset: int,
        ) -> TicketAnalyticsRow:
            return TicketAnalyticsRow(
                lottery_id,
                name,
                active,
                *(int(value or 0) for value in values[offset : offset + 8]),
            )

        return TicketAnalytics(
            overall=row(
                overall_values,
                lottery_id=None,
                name="Все лотереи",
                active=None,
                offset=0,
            ),
            lotteries=tuple(
                row(
                    values,
                    lottery_id=values[0],
                    name=values[1],
                    active=values[2],
                    offset=3,
                )
                for values in lottery_values
            ),
        )

    async def activity(self, *, period_days: int) -> tuple[AdminActivityPoint, ...]:
        """Return compact draw activity buckets for the owner dashboard."""

        bucket = "hour" if period_days == 1 else "day"
        bucket_at = func.date_trunc(bucket, Draw.scheduled_at).label("bucket_at")
        rows = (
            await self._session.execute(
                select(
                    bucket_at,
                    func.coalesce(func.sum(Draw.ticket_count), 0),
                    func.coalesce(func.sum(Draw.total_sales), 0),
                    func.coalesce(func.sum(Draw.total_payout), 0),
                )
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .where(
                    lottery_scope(self._scope),
                    Draw.status == DrawStatus.COMPLETED,
                    Draw.scheduled_at
                    >= datetime.now(UTC) - timedelta(days=period_days),
                )
                .group_by(bucket_at)
                .order_by(bucket_at)
            )
        ).all()
        return tuple(
            AdminActivityPoint(
                bucket_at=row[0],
                ticket_count=int(row[1]),
                total_sales=int(row[2]),
                total_payout=int(row[3]),
            )
            for row in rows
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
        tickets = await self._session.scalar(
            select(func.count(Ticket.id))
            .join(Draw, Draw.id == Ticket.draw_id)
            .join(Lottery, Lottery.id == Draw.lottery_id)
            .where(lottery_scope(self._scope))
        )
        completed = await self._session.scalar(
            select(func.count(Draw.id))
            .join(Lottery, Lottery.id == Draw.lottery_id)
            .where(Draw.status == DrawStatus.COMPLETED, lottery_scope(self._scope))
        )
        pending = await self._session.scalar(
            select(func.count(Draw.id))
            .join(Lottery, Lottery.id == Draw.lottery_id)
            .where(
                or_(
                    Draw.status == DrawStatus.SCHEDULED,
                    Draw.status == DrawStatus.CLOSED,
                    Draw.status == DrawStatus.DRAWING,
                    Draw.status == DrawStatus.SETTLING,
                    Draw.status == DrawStatus.FAILED,
                ),
                lottery_scope(self._scope),
            )
        )
        return {
            "users": users or 0,
            "tickets": tickets or 0,
            "completed_draws": completed or 0,
            "pending_draws": pending or 0,
        }

    async def today_summary(self, *, now: datetime | None = None) -> dict[str, int]:
        """Owner-facing Moscow-day sales and payout snapshot."""
        timestamp = now or datetime.now(UTC)
        local_day = timestamp.astimezone(MOSCOW).date()
        start = datetime.combine(
            local_day, datetime.min.time(), tzinfo=MOSCOW
        ).astimezone(UTC)
        end = start + timedelta(days=1)
        completed = await self._session.scalar(
            select(func.count(Draw.id))
            .join(Lottery, Lottery.id == Draw.lottery_id)
            .where(
                Draw.status == DrawStatus.COMPLETED,
                Draw.scheduled_at >= start,
                Draw.scheduled_at < end,
                lottery_scope(self._scope),
            )
        )
        ticket_count, sales = (
            await self._session.execute(
                select(
                    func.count(Ticket.id),
                    func.coalesce(func.sum(Ticket.purchase_price), 0),
                )
                .join(Draw, Draw.id == Ticket.draw_id)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .where(
                    Ticket.purchased_at >= start,
                    Ticket.purchased_at < end,
                    lottery_scope(self._scope),
                )
            )
        ).one()
        winning_tickets, payout = (
            await self._session.execute(
                select(
                    func.count(Ticket.id).filter(Ticket.prize_amount > 0),
                    func.coalesce(func.sum(Ticket.prize_amount), 0),
                )
                .join(Draw, Draw.id == Ticket.draw_id)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .where(
                    Ticket.settled_at >= start,
                    Ticket.settled_at < end,
                    lottery_scope(self._scope),
                )
            )
        ).one()
        sales_value = int(sales)
        payout_value = int(payout)
        return {
            "completed_draws": int(completed or 0),
            "purchased_tickets": int(ticket_count),
            "sales": sales_value,
            "winning_tickets": int(winning_tickets),
            "payout": payout_value,
            "net": sales_value - payout_value,
        }

    async def jackpot_analytics(self) -> dict[str, Any]:
        """Aggregate all events independently of the bounded history."""
        fund = await self._session.scalar(select(KasperFundAccount).limit(1))
        events = (
            await self._session.execute(
                select(JackpotWinEvent, Lottery, Draw.public_number)
                .join(Lottery, Lottery.id == JackpotWinEvent.lottery_id)
                .join(Draw, Draw.id == JackpotWinEvent.draw_id)
                .where(lottery_scope(self._scope))
                .order_by(JackpotWinEvent.occurred_at.desc(), JackpotWinEvent.id.desc())
                .limit(50)
            )
        ).all()
        totals = (
            await self._session.execute(
                select(
                    func.count(JackpotWinEvent.id),
                    func.coalesce(func.sum(JackpotWinEvent.jackpot_amount), 0),
                    func.coalesce(func.max(JackpotWinEvent.jackpot_amount), 0),
                )
                .join(Lottery, Lottery.id == JackpotWinEvent.lottery_id)
                .where(lottery_scope(self._scope))
            )
        ).one()
        grouped = (
            await self._session.execute(
                select(
                    Lottery.id,
                    Lottery.code,
                    Lottery.name,
                    Lottery.is_active,
                    func.count(JackpotWinEvent.id),
                    func.coalesce(func.sum(JackpotWinEvent.jackpot_amount), 0),
                    func.max(JackpotWinEvent.occurred_at),
                    func.coalesce(func.max(JackpotWinEvent.jackpot_amount), 0),
                )
                .outerjoin(JackpotWinEvent, JackpotWinEvent.lottery_id == Lottery.id)
                .where(lottery_scope(self._scope))
                .group_by(Lottery.id)
                .order_by(Lottery.is_active.desc(), Lottery.code)
            )
        ).all()
        ranked = select(
            JackpotWinEvent.id.label("event_id"),
            func.row_number()
            .over(
                partition_by=JackpotWinEvent.lottery_id,
                order_by=(
                    JackpotWinEvent.occurred_at.desc(),
                    JackpotWinEvent.id.desc(),
                ),
            )
            .label("position"),
        ).subquery()
        last_rows = (
            await self._session.execute(
                select(JackpotWinEvent, Draw.public_number)
                .join(ranked, ranked.c.event_id == JackpotWinEvent.id)
                .join(Draw, Draw.id == JackpotWinEvent.draw_id)
                .where(ranked.c.position == 1)
            )
        ).all()
        last_by_lottery = {
            event.lottery_id: (event, number) for event, number in last_rows
        }
        history = [
            {
                "id": str(event.id),
                "lottery_code": lottery.code,
                "lottery_name": lottery.name,
                "draw_id": str(event.draw_id),
                "draw_number": number,
                "jackpot_amount": event.jackpot_amount,
                "winner_ticket_count": event.winner_ticket_count,
                "winner_user_count": event.winner_user_count,
                "base_jackpot_after": event.base_jackpot_after,
                "occurred_at": event.occurred_at,
            }
            for event, lottery, number in events
        ]
        lottery_rows = []
        for lottery_id, code, name, active, count, total, last_at, largest in grouped:
            latest = last_by_lottery.get(lottery_id)
            lottery_rows.append(
                {
                    "lottery_id": str(lottery_id),
                    "code": code,
                    "name": name,
                    "is_active": active,
                    "win_count": int(count),
                    "total_paid": int(total),
                    "last_win_at": last_at,
                    "largest_win": int(largest),
                    "last_win_amount": latest[0].jackpot_amount if latest else None,
                    "last_draw_id": str(latest[0].draw_id) if latest else None,
                    "last_draw_number": latest[1] if latest else None,
                }
            )
        return {
            "kasper_fund_balance": fund.balance if fund else 0,
            "total_wins": int(totals[0]),
            "total_paid": int(totals[1]),
            "largest_win": int(totals[2]),
            "lotteries": lottery_rows,
            "last_win": history[0] if history else None,
            "history": history,
        }

    async def operational_status(self) -> dict[str, Any]:
        """Return a cheap, read-only control-room projection for the owner."""
        now = datetime.now(UTC)
        heartbeat = await self._session.get(SchedulerHeartbeat, 1)
        next_rows = (
            await self._session.execute(
                select(
                    Draw,
                    Lottery,
                    func.count(Ticket.id),
                    func.count(func.distinct(Ticket.user_id)),
                )
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .outerjoin(Ticket, Ticket.draw_id == Draw.id)
                .where(Draw.status != DrawStatus.COMPLETED, lottery_scope(self._scope))
                .group_by(Draw.id, Lottery.id)
                .order_by(Draw.scheduled_at)
                .limit(8)
            )
        ).all()
        notification_rows = (
            await self._session.execute(
                select(
                    NotificationOutbox.status, func.count(NotificationOutbox.id)
                ).group_by(NotificationOutbox.status)
            )
        ).all()
        stuck_count = int(
            await self._session.scalar(
                select(func.count(Draw.id)).where(
                    Draw.status != DrawStatus.COMPLETED,
                    Draw.scheduled_at < now - timedelta(minutes=5),
                )
            )
            or 0
        )
        return {
            "today": await self.today_summary(now=now),
            "scheduler": {
                "last_started_at": heartbeat.last_started_at if heartbeat else None,
                "last_succeeded_at": (
                    heartbeat.last_succeeded_at if heartbeat else None
                ),
                "last_failed_at": heartbeat.last_failed_at if heartbeat else None,
                "last_error": heartbeat.last_error if heartbeat else None,
                "settled_count": heartbeat.settled_count if heartbeat else 0,
                "prepared_count": heartbeat.prepared_count if heartbeat else 0,
            },
            "stuck_draw_count": stuck_count,
            "notifications": {
                status.value: int(count) for status, count in notification_rows
            },
            "next_draws": [
                {
                    "id": str(draw.id),
                    "lottery_name": draw_display_name(
                        lottery.code, lottery.name, draw.scheduled_at
                    ),
                    "draw_number": draw.public_number,
                    "scheduled_at": draw.scheduled_at,
                    "sales_close_at": draw.sales_close_at,
                    "status": draw.status.value,
                    "ticket_count": int(ticket_count),
                    "participant_count": int(participant_count),
                    "total_sales": draw.total_sales,
                }
                for draw, lottery, ticket_count, participant_count in next_rows
            ],
        }

    async def notifications(
        self,
        *,
        status: NotificationStatus | None = None,
        user_id: UUID | None = None,
        limit: int = 200,
    ) -> tuple[AdminNotification, ...]:
        statement = select(NotificationOutbox)
        if status is not None:
            statement = statement.where(NotificationOutbox.status == status)
        if user_id is not None:
            statement = statement.where(NotificationOutbox.user_id == user_id)
        rows = (
            await self._session.scalars(
                statement.order_by(NotificationOutbox.created_at.desc()).limit(limit)
            )
        ).all()
        return tuple(
            AdminNotification(
                row.id,
                row.event_key,
                row.user_id,
                row.type,
                row.status,
                row.attempts,
                row.available_at,
                row.sent_at,
                row.last_error,
                row.created_at,
            )
            for row in rows
        )
