"""Read models for the Telegram Mini App."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4
from weakref import WeakKeyDictionary
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, literal, or_, select, text, union_all, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from k_loto.application.display_cache import DisplayCache, PlatformTotalsCache
from k_loto.application.query_scope import LotteryScope, lottery_scope
from k_loto.application.ticket_history import TicketHistoryService
from k_loto.domain.dual import dual_phase
from k_loto.domain.enums import (
    DrawStatus,
    InAppNotificationType,
    LedgerAccountKind,
    LotteryKind,
    NotificationStatus,
    NotificationType,
    TicketSource,
    TicketStatus,
    TransactionType,
)
from k_loto.domain.instant import (
    INSTANT_GAMES,
    instant_rules_for_version,
    instant_versions,
)
from k_loto.domain.live_timeline import (
    draw_timeline,
    fast_presentation_timeline,
    khan_presentation_timeline,
    presentation_timeline,
    sales_status,
)
from k_loto.domain.lotteries import (
    FAST_LOTTERY_CODES,
    draw_display_code,
    draw_display_name,
)
from k_loto.domain.lottery_rules import get_lottery_rules
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    InstantTicket,
    JackpotAccount,
    JackpotWinEvent,
    LedgerTransaction,
    Lottery,
    NotificationOutbox,
    PlayerLotteryStats,
    PlayerProfileStats,
    Ticket,
    User,
    UserNotification,
    UserNotificationPreference,
)

_platform_caches: WeakKeyDictionary[AsyncEngine, PlatformTotalsCache] = (
    WeakKeyDictionary()
)


@dataclass(frozen=True, slots=True)
class MiniAppLottery:
    code: str
    name: str
    ruleset_code: str
    kind: LotteryKind
    numbers_to_pick: int
    max_number: int
    primary_numbers_to_pick: int
    primary_max_number: int
    secondary_numbers_to_pick: int
    secondary_max_number: int
    secondary_storage_offset: int
    ticket_price: int | None
    jackpot: int
    draw_number: int | None
    scheduled_at: datetime | None
    sales_close_at: datetime | None
    sales_open: bool
    purchase_available: bool
    player_ticket_count: int
    sales_status: str
    max_tickets_per_purchase: int
    max_tickets_per_user_per_draw: int
    fixed_payouts: dict[int, int] | None = None
    is_distribution: bool = False


@dataclass(frozen=True, slots=True)
class MiniAppTicket:
    id: UUID
    public_number: int
    lottery_code: str
    lottery_name: str
    draw_number: int
    scheduled_at: datetime
    numbers: tuple[int, ...]
    purchase_price: int
    source: TicketSource
    status: TicketStatus
    matches: int | None
    prize_amount: int
    winning_numbers: tuple[int, ...] | None
    draw_ticket_count: int
    bingo_result: dict[str, Any] | None = None
    instant_symbols: tuple[int, ...] | None = None
    second_draw_number: int | None = None
    second_scheduled_at: datetime | None = None
    first_phase: str | None = None
    first_winning_numbers: tuple[int, ...] | None = None
    second_winning_numbers: tuple[int, ...] | None = None
    dual_night_matches: int | None = None
    dual_dawn_matches: int | None = None
    primary_max_number: int | None = None


@dataclass(frozen=True, slots=True)
class MiniAppDashboard:
    server_time: datetime
    balance: int
    active_ticket_count: int
    lotteries: tuple[MiniAppLottery, ...]
    recent_results: tuple[MiniAppTicket, ...]
    monthly_total_payout: int
    total_ticket_count: int
    total_winning_ticket_count: int


@dataclass(frozen=True, slots=True)
class MiniAppDrawResult:
    lottery_code: str
    lottery_name: str
    draw_number: int
    scheduled_at: datetime
    executed_at: datetime | None
    winning_numbers: tuple[int, ...]
    ticket_count: int
    total_payout: int


@dataclass(frozen=True, slots=True)
class MiniAppLiveTicket:
    public_number: int
    numbers: tuple[int, ...]
    matches: int | None
    prize_amount: int


@dataclass(frozen=True, slots=True)
class MiniAppLiveDraw:
    lottery_code: str
    lottery_name: str
    lottery_kind: LotteryKind
    draw_number: int
    scheduled_at: datetime
    status: DrawStatus
    winning_numbers: tuple[int, ...] | None
    jackpot: int
    player_ticket_count: int
    player_winning_ticket_count: int
    player_best_matches: int | None
    player_total_prize: int
    highlighted_tickets: tuple[MiniAppLiveTicket, ...]
    sales_close_at: datetime
    sales_status: str
    live_starts_at: datetime
    reveal_at: tuple[datetime, ...]
    live_ends_at: datetime
    primary_numbers_to_pick: int = 0
    secondary_storage_offset: int = 0
    primary_max_number: int = 0
    is_distribution: bool = False


@dataclass(frozen=True, slots=True)
class MiniAppLiveFeed:
    server_time: datetime
    latest_completed: MiniAppLiveDraw | None
    next_scheduled: MiniAppLiveDraw | None
    recent_completed: tuple[MiniAppLiveDraw, ...]


@dataclass(frozen=True, slots=True)
class PublicLiveDraw:
    draw_id: UUID
    code: str
    value: MiniAppLiveDraw


@dataclass(frozen=True, slots=True)
class PublicLiveFeed:
    recent: tuple[PublicLiveDraw, ...]
    upcoming: PublicLiveDraw | None


_live_caches: WeakKeyDictionary[
    AsyncEngine, DisplayCache[tuple[bool, str | None], PublicLiveFeed]
] = WeakKeyDictionary()


@dataclass(frozen=True, slots=True)
class PlayerActivity:
    type: TransactionType
    amount: int
    balance_after: int
    lottery_name: str | None
    created_at: datetime
    details: dict[str, object]


@dataclass(frozen=True, slots=True)
class MiniAppNotificationPreferences:
    telegram_enabled: bool
    draw_results_enabled: bool
    inactivity_reminders_enabled: bool


@dataclass(frozen=True, slots=True)
class MiniAppAccount:
    display_name: str
    balance: int
    ticket_count: int
    active_ticket_count: int
    winning_ticket_count: int
    total_spent: int
    total_won: int
    best_win: int
    favorite_lottery_code: str | None
    favorite_lottery_name: str | None
    favorite_numbers: tuple[int, ...]
    unread_notification_count: int
    notification_preferences: MiniAppNotificationPreferences


@dataclass(frozen=True, slots=True)
class MiniAppNotification:
    id: UUID
    type: InAppNotificationType
    title: str
    body: str
    payload: dict[str, object]
    read_at: datetime | None
    created_at: datetime


class MiniAppQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def highlights(
        self, user_id: UUID, *, scope: LotteryScope = "standard"
    ) -> dict[str, Any]:
        row = (
            await self._session.execute(
                select(JackpotWinEvent, Lottery, Draw.public_number)
                .join(Lottery, Lottery.id == JackpotWinEvent.lottery_id)
                .join(Draw, Draw.id == JackpotWinEvent.draw_id)
                .where(lottery_scope(scope))
                .order_by(JackpotWinEvent.occurred_at.desc(), JackpotWinEvent.id.desc())
                .limit(1)
            )
        ).first()
        last = None
        if row is not None:
            event, lottery, number = row
            last = {
                "lottery_code": lottery.code,
                "lottery_name": lottery.name,
                "draw_number": number,
                "jackpot_amount": event.jackpot_amount,
                "occurred_at": event.occurred_at,
            }
        now = datetime.now(UTC)
        upcoming = (
            await self._session.execute(
                select(Draw, Lottery.code, JackpotAccount.balance)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .join(JackpotAccount, JackpotAccount.lottery_id == Lottery.id)
                .where(
                    lottery_scope(scope),
                    Lottery.is_active.is_(True),
                    or_(
                        Draw.status.not_in(
                            (DrawStatus.COMPLETED, DrawStatus.CANCELLED)
                        ),
                        Draw.executed_at >= now - timedelta(seconds=150),
                    ),
                )
                .order_by(Draw.scheduled_at)
                .limit(1)
            )
        ).first()
        next_event = None
        if upcoming:
            draw, code, jackpot = upcoming
            count = await self._session.scalar(
                select(func.count(Ticket.id)).where(
                    Ticket.draw_id == draw.id, Ticket.user_id == user_id
                )
            )
            phase = (
                "result"
                if draw.status == DrawStatus.COMPLETED
                else "live"
                if now >= draw.scheduled_at
                else "waiting"
            )
            next_event = {
                "lottery_code": code,
                "scheduled_at": draw.scheduled_at,
                "draw_number": draw.public_number,
                "player_ticket_count": int(count or 0),
                "jackpot": draw.jackpot_opening
                if phase != "waiting" and draw.jackpot_opening is not None
                else jackpot,
                "phase": phase,
            }
        return {"last_jackpot": last, "next_event": next_event}

    async def account(self, user_id: UUID) -> MiniAppAccount:
        row = (
            await self._session.execute(
                select(
                    User, Balance.amount, PlayerProfileStats, UserNotificationPreference
                )
                .join(PlayerProfileStats, PlayerProfileStats.user_id == User.id)
                .outerjoin(Balance, Balance.user_id == User.id)
                .outerjoin(
                    UserNotificationPreference,
                    UserNotificationPreference.user_id == User.id,
                )
                .where(User.id == user_id)
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        if row is None:
            raise LookupError("Player or profile projection does not exist.")
        user, balance, stats, preference = row
        favorite_lottery = (
            await self._session.execute(
                select(Lottery.id, Lottery.code, Lottery.name)
                .join(PlayerLotteryStats, PlayerLotteryStats.lottery_id == Lottery.id)
                .where(
                    PlayerLotteryStats.user_id == user_id,
                    PlayerLotteryStats.ticket_count > 0,
                )
                .order_by(PlayerLotteryStats.ticket_count.desc(), Lottery.code)
                .limit(1)
            )
        ).first()
        favorite_numbers: tuple[int, ...] = ()
        if favorite_lottery is not None:
            # Limit before unnest/grouping: old tickets never enter this calculation.
            recent = (
                select(Ticket.numbers)
                .where(
                    Ticket.user_id == user_id,
                    Ticket.lottery_id == favorite_lottery.id,
                    text("tickets.status <> 'REFUNDED'"),
                )
                .order_by(Ticket.purchased_at.desc(), Ticket.id.desc())
                .limit(1_000)
                .subquery()
            )
            numbers = select(func.unnest(recent.c.numbers).label("number")).subquery()
            favorite_numbers = tuple(
                await self._session.scalars(
                    select(numbers.c.number)
                    .group_by(numbers.c.number)
                    .order_by(func.count().desc(), numbers.c.number.asc())
                    .limit(7)
                )
            )
        return MiniAppAccount(
            display_name=user.display_name,
            balance=int(balance or 0),
            ticket_count=stats.ticket_count,
            active_ticket_count=stats.active_ticket_count,
            winning_ticket_count=stats.winning_ticket_count,
            total_spent=stats.total_spent,
            total_won=stats.total_won,
            best_win=stats.best_win,
            favorite_lottery_code=(
                str(favorite_lottery.code) if favorite_lottery is not None else None
            ),
            favorite_lottery_name=(
                draw_display_name(
                    str(favorite_lottery.code),
                    str(favorite_lottery.name),
                    datetime.now(UTC),
                )
                if favorite_lottery is not None
                else None
            ),
            favorite_numbers=favorite_numbers,
            unread_notification_count=stats.unread_notification_count,
            notification_preferences=MiniAppNotificationPreferences(
                telegram_enabled=bool(preference and preference.telegram_enabled),
                draw_results_enabled=(
                    preference.draw_results_enabled if preference else True
                ),
                inactivity_reminders_enabled=(
                    preference.inactivity_reminders_enabled if preference else True
                ),
            ),
        )

    async def notifications(
        self, user_id: UUID, *, limit: int = 100
    ) -> tuple[MiniAppNotification, ...]:
        rows = (
            await self._session.scalars(
                select(UserNotification)
                .where(
                    UserNotification.user_id == user_id,
                    UserNotification.type != InAppNotificationType.DRAW_RESULT,
                )
                .order_by(UserNotification.created_at.desc())
                .limit(limit)
            )
        ).all()
        return tuple(
            MiniAppNotification(
                item.id,
                item.type,
                item.title,
                item.body,
                item.payload,
                item.read_at,
                item.created_at,
            )
            for item in rows
        )

    async def set_notification_preferences(
        self,
        user_id: UUID,
        *,
        telegram_enabled: bool,
        draw_results_enabled: bool,
        inactivity_reminders_enabled: bool,
        now: datetime | None = None,
    ) -> MiniAppNotificationPreferences:
        timestamp = now or datetime.now(UTC)
        async with self._session.begin():
            preference = await self._session.get(
                UserNotificationPreference, user_id, with_for_update=True
            )
            if preference is None:
                preference = UserNotificationPreference(user_id=user_id)
                self._session.add(preference)
            preference.telegram_enabled = telegram_enabled
            preference.draw_results_enabled = draw_results_enabled
            preference.inactivity_reminders_enabled = inactivity_reminders_enabled
            if telegram_enabled and preference.write_access_granted_at is None:
                preference.write_access_granted_at = timestamp
        return MiniAppNotificationPreferences(
            telegram_enabled,
            draw_results_enabled,
            inactivity_reminders_enabled,
        )

    async def mark_notifications_read(
        self, user_id: UUID, notification_id: UUID | None = None
    ) -> None:
        timestamp = datetime.now(UTC)
        filters = [
            UserNotification.user_id == user_id,
            UserNotification.read_at.is_(None),
        ]
        if notification_id is not None:
            filters.append(UserNotification.id == notification_id)
        async with self._session.begin():
            await self._session.execute(
                update(UserNotification).where(*filters).values(read_at=timestamp)
            )

    async def queue_delivery_test(
        self, user_id: UUID, *, now: datetime | None = None
    ) -> bool:
        """Queue at most one explicit delivery diagnostic per user and hour."""

        timestamp = now or datetime.now(UTC)
        async with self._session.begin():
            preference = await self._session.get(UserNotificationPreference, user_id)
            if preference is None or not preference.telegram_enabled:
                raise PermissionError("Telegram notifications are not enabled.")
            event_key = f"delivery-test:{user_id}:{int(timestamp.timestamp() // 3600)}"
            exists = await self._session.scalar(
                select(NotificationOutbox.id).where(
                    NotificationOutbox.event_key == event_key
                )
            )
            if exists is not None:
                return False
            self._session.add(
                NotificationOutbox(
                    id=uuid4(),
                    event_key=event_key,
                    user_id=user_id,
                    type=NotificationType.DELIVERY_TEST,
                    status=NotificationStatus.PENDING,
                    payload={"requested_at": timestamp.isoformat()},
                    attempts=0,
                    available_at=timestamp,
                )
            )
        return True

    async def dashboard(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
        include_recent_results: bool = True,
    ) -> MiniAppDashboard:
        timestamp = now or datetime.now(UTC)
        balance = await self._session.scalar(
            select(Balance.amount).where(Balance.user_id == user_id)
        )
        if balance is None:
            balance = 0
        active_count = await self._session.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.user_id == user_id,
                Ticket.status == TicketStatus.PURCHASED,
            )
        )
        lottery_rows = (
            await self._session.execute(
                select(Lottery, JackpotAccount.balance)
                .outerjoin(JackpotAccount, JackpotAccount.lottery_id == Lottery.id)
                .where(Lottery.is_active.is_(True))
                .order_by(Lottery.kind, Lottery.name)
            )
        ).all()
        open_draws = (
            await self._session.scalars(
                select(Draw)
                .where(
                    Draw.lottery_id.in_([row.id for row, _ in lottery_rows]),
                    Draw.status == DrawStatus.SCHEDULED,
                    Draw.scheduled_at > timestamp,
                    Draw.sales_close_at > timestamp,
                )
                .distinct(Draw.lottery_id)
                .order_by(Draw.lottery_id, Draw.scheduled_at, Draw.id)
            )
        ).all()
        by_lottery = {draw.lottery_id: draw for draw in open_draws}
        draw_ids = [draw.id for draw in open_draws]
        primary_counts = (
            select(
                Ticket.draw_id.label("draw_id"), func.count(Ticket.id).label("count")
            )
            .where(
                Ticket.user_id == user_id,
                Ticket.status == TicketStatus.PURCHASED,
                Ticket.draw_id.in_(draw_ids),
            )
            .group_by(Ticket.draw_id)
        )
        secondary_counts = (
            select(
                Ticket.second_draw_id.label("draw_id"),
                func.count(Ticket.id).label("count"),
            )
            .where(
                Ticket.user_id == user_id,
                Ticket.status == TicketStatus.PURCHASED,
                Ticket.second_draw_id.in_(draw_ids),
            )
            .group_by(Ticket.second_draw_id)
        )
        player_counts: dict[UUID, int] = {}
        for draw_id, count in (
            await self._session.execute(primary_counts.union_all(secondary_counts))
        ).all():
            player_counts[draw_id] = player_counts.get(draw_id, 0) + count
        lotteries: list[MiniAppLottery] = []
        for lottery, jackpot in lottery_rows:
            draw = by_lottery.get(lottery.id)
            sales_open = draw is not None and draw.sales_close_at > timestamp
            snapshot = (draw.configuration_snapshot or {}) if draw is not None else {}
            rules = get_lottery_rules(
                str(snapshot.get("ruleset_code", lottery.ruleset_code))
            )
            draw_ticket_price = (
                int(snapshot["ticket_price"])
                if snapshot.get("ticket_price") is not None
                else lottery.ticket_price
            )
            purchase_available = draw_ticket_price is not None and sales_open
            player_ticket_count = player_counts.get(draw.id, 0) if draw else 0
            timeline = (
                draw_timeline(
                    draw.scheduled_at,
                    2 if lottery.code == "dual" else rules.numbers_to_pick,
                )
                if draw is not None
                else None
            )
            lotteries.append(
                MiniAppLottery(
                    code=lottery.code,
                    name=(
                        draw_display_name(lottery.code, lottery.name, draw.scheduled_at)
                        if draw
                        else lottery.name
                    ),
                    ruleset_code=rules.code,
                    kind=lottery.kind,
                    numbers_to_pick=rules.numbers_to_pick,
                    max_number=rules.max_number,
                    primary_numbers_to_pick=rules.display_primary_numbers_to_pick,
                    primary_max_number=rules.display_primary_max_number,
                    secondary_numbers_to_pick=rules.secondary_numbers_to_pick,
                    secondary_max_number=rules.secondary_max_number,
                    secondary_storage_offset=rules.secondary_storage_offset,
                    ticket_price=draw_ticket_price,
                    jackpot=jackpot or 0,
                    draw_number=draw.public_number if draw else None,
                    scheduled_at=draw.scheduled_at if draw else None,
                    sales_close_at=draw.sales_close_at if draw else None,
                    sales_open=sales_open,
                    purchase_available=purchase_available,
                    player_ticket_count=player_ticket_count,
                    sales_status=(
                        sales_status(
                            now=timestamp,
                            status=draw.status,
                            sales_close_at=draw.sales_close_at,
                            timeline=timeline,
                        )
                        if draw is not None and timeline is not None
                        else "CLOSED"
                    ),
                    max_tickets_per_purchase=lottery.max_tickets_per_purchase,
                    max_tickets_per_user_per_draw=lottery.max_tickets_per_user_per_draw,
                    fixed_payouts=dict(rules.fixed_payouts),
                    is_distribution=bool(draw and draw.is_distribution),
                )
            )
        recent_results = (
            await self.tickets(user_id, active=False, limit=3)
            if include_recent_results
            else ()
        )
        moscow_now = timestamp.astimezone(ZoneInfo("Europe/Moscow"))
        month_start_local = moscow_now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        month_start = month_start_local.astimezone(UTC)

        async def load_totals() -> tuple[int, int, int]:
            return await self._platform_totals(month_start)

        bind = getattr(self._session, "bind", None)
        if isinstance(bind, AsyncEngine):
            cache = _platform_caches.setdefault(bind, PlatformTotalsCache())
            monthly_total_payout, total_tickets, winning_tickets = await cache.get(
                month_start, load_totals
            )
        else:
            monthly_total_payout, total_tickets, winning_tickets = await load_totals()
        return MiniAppDashboard(
            server_time=timestamp,
            balance=balance,
            active_ticket_count=active_count or 0,
            lotteries=tuple(lotteries),
            recent_results=recent_results,
            monthly_total_payout=monthly_total_payout,
            total_ticket_count=total_tickets,
            total_winning_ticket_count=winning_tickets,
        )

    async def _platform_totals(self, month_start: datetime) -> tuple[int, int, int]:
        monthly_total_payout = int(
            await self._session.scalar(
                select(func.coalesce(func.sum(Draw.total_payout), 0)).where(
                    Draw.status == DrawStatus.COMPLETED,
                    Draw.executed_at >= month_start,
                )
            )
            or 0
        )
        monthly_total_payout += int(
            await self._session.scalar(
                select(func.coalesce(func.sum(InstantTicket.prize_amount), 0)).where(
                    InstantTicket.settled_at >= month_start
                )
            )
            or 0
        )
        ticket_totals = (
            await self._session.execute(
                select(
                    func.count(Ticket.id),
                    func.count(Ticket.id).filter(Ticket.prize_amount > 0),
                )
            )
        ).one()
        instant_ticket_totals = (
            await self._session.execute(
                select(
                    func.count(InstantTicket.id),
                    func.count(InstantTicket.id).filter(InstantTicket.prize_amount > 0),
                )
            )
        ).one()
        return (
            monthly_total_payout,
            int(ticket_totals[0]) + int(instant_ticket_totals[0]),
            int(ticket_totals[1]) + int(instant_ticket_totals[1]),
        )

    @staticmethod
    def _draw_ticket(
        ticket: Ticket,
        draw: Draw,
        second: Draw | None,
        lottery: Lottery,
        draw_ticket_count: int,
    ) -> MiniAppTicket:
        return MiniAppTicket(
            id=ticket.id,
            public_number=ticket.public_number,
            lottery_code=lottery.code,
            lottery_name=draw_display_name(
                lottery.code, lottery.name, draw.scheduled_at
            ),
            draw_number=draw.public_number,
            scheduled_at=(
                second.scheduled_at
                if lottery.code == "dual"
                and second is not None
                and draw.status == DrawStatus.COMPLETED
                and ticket.status == TicketStatus.PURCHASED
                else draw.scheduled_at
            ),
            numbers=tuple(ticket.numbers),
            purchase_price=ticket.purchase_price,
            source=ticket.source,
            status=ticket.status,
            matches=ticket.matches,
            prize_amount=ticket.prize_amount,
            winning_numbers=(
                tuple(draw.winning_numbers)
                if draw.winning_numbers
                and lottery.code != "dual"
                and (lottery.code != "bingo" or draw.status == DrawStatus.COMPLETED)
                else None
            ),
            draw_ticket_count=int(draw_ticket_count),
            bingo_result=ticket.bingo_result,
            primary_max_number=(
                16
                if lottery.code == "grob" and ticket.status == TicketStatus.REFUNDED
                else int(
                    (draw.configuration_snapshot or {}).get(
                        "max_number", lottery.max_number
                    )
                )
                if lottery.code == "grob"
                else None
            ),
            second_draw_number=second.public_number if second is not None else None,
            second_scheduled_at=second.scheduled_at if second is not None else None,
            first_phase=dual_phase(draw.scheduled_at)
            if lottery.code == "dual"
            else None,
            first_winning_numbers=tuple(draw.winning_numbers)
            if lottery.code == "dual" and draw.winning_numbers
            else None,
            second_winning_numbers=tuple(second.winning_numbers)
            if second is not None and second.winning_numbers
            else None,
            dual_night_matches=ticket.dual_night_matches,
            dual_dawn_matches=ticket.dual_dawn_matches,
        )

    @staticmethod
    def _instant_ticket(item: InstantTicket) -> MiniAppTicket:
        return MiniAppTicket(
            id=item.id,
            public_number=item.public_number,
            lottery_code=instant_rules_for_version(item.odds_version).code,
            lottery_name=instant_rules_for_version(item.odds_version).name,
            draw_number=0,
            scheduled_at=item.purchased_at,
            numbers=(),
            purchase_price=item.purchase_price,
            source=TicketSource.MANUAL,
            status=TicketStatus.SETTLED,
            matches=None,
            prize_amount=item.prize_amount,
            winning_numbers=None,
            draw_ticket_count=1,
            instant_symbols=tuple(item.symbols),
        )

    async def history_page(
        self,
        user_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
        cursor: str | None = None,
        lottery_code: str | None = None,
        wins_only: bool = False,
        scope: LotteryScope = "all",
    ) -> tuple[tuple[MiniAppTicket, ...], str | None, bool]:
        page = await TicketHistoryService(self._session).page(
            user_id,
            limit=limit,
            offset=offset,
            cursor=cursor,
            lottery_code=lottery_code,
            wins_only=wins_only,
            scope=scope,
        )
        views = {
            ("DRAW", ticket.id): self._draw_ticket(
                ticket, draw, second, lottery, int(count)
            )
            for ticket, draw, second, lottery, count in page.draw_rows
        }
        views.update(
            {
                ("INSTANT", item.id): self._instant_ticket(item)
                for item in page.instant_rows
            }
        )
        return tuple(views[key] for key in page.keys), page.next_cursor, page.has_more

    async def tickets(
        self,
        user_id: UUID,
        *,
        active: bool,
        limit: int = 100,
        offset: int = 0,
        lottery_code: str | None = None,
        wins_only: bool = False,
        scope: LotteryScope = "all",
    ) -> tuple[MiniAppTicket, ...]:
        only_instant = lottery_code in INSTANT_GAMES
        include_instant = not active and (
            (not lottery_code and scope == "all") or only_instant
        )
        filters = [Ticket.user_id == user_id, lottery_scope(scope)]
        if active:
            filters.append(Ticket.status == TicketStatus.PURCHASED)
        else:
            filters.append(
                Ticket.status.in_((TicketStatus.SETTLED, TicketStatus.REFUNDED))
            )
        if lottery_code and not only_instant:
            filters.append(Lottery.code == lottery_code)
        if wins_only:
            filters.append(Ticket.prize_amount > 0)
        ordering = (
            (Draw.scheduled_at.asc(), Ticket.public_number.desc())
            if active
            else (Draw.scheduled_at.desc(), Ticket.public_number.desc())
        )
        regular: list[MiniAppTicket] = []
        if not only_instant:
            second_draw = aliased(Draw)
            group_ticket = aliased(Ticket)
            group_count = select(func.count(group_ticket.id)).where(
                group_ticket.user_id == user_id,
                group_ticket.draw_id == Ticket.draw_id,
                group_ticket.status == TicketStatus.PURCHASED
                if active
                else group_ticket.status.in_(
                    (TicketStatus.SETTLED, TicketStatus.REFUNDED)
                ),
            )
            if wins_only:
                group_count = group_count.where(group_ticket.prize_amount > 0)
            regular_rows = (
                await self._session.execute(
                    select(
                        Ticket,
                        Draw,
                        second_draw,
                        Lottery,
                        group_count.correlate(Ticket).scalar_subquery(),
                    )
                    .join(Draw, Draw.id == Ticket.draw_id)
                    .outerjoin(second_draw, second_draw.id == Ticket.second_draw_id)
                    .join(Lottery, Lottery.id == Ticket.lottery_id)
                    .where(*filters)
                    .order_by(*ordering)
                    .limit(limit + offset if include_instant else limit)
                    .offset(0 if include_instant else offset)
                )
            ).all()
            regular = [
                self._draw_ticket(ticket, draw, second, lottery, int(count))
                for ticket, draw, second, lottery, count in regular_rows
            ]
        if not include_instant:
            return tuple(regular)
        instant_filters = [InstantTicket.user_id == user_id]
        if only_instant and lottery_code:
            instant_filters.append(
                InstantTicket.odds_version.in_(instant_versions(lottery_code))
            )
        if wins_only:
            instant_filters.append(InstantTicket.prize_amount > 0)
        instant_rows = (
            await self._session.scalars(
                select(InstantTicket)
                .where(*instant_filters)
                .order_by(
                    InstantTicket.purchased_at.desc(),
                    InstantTicket.public_number.desc(),
                )
                .limit(limit + offset)
            )
        ).all()
        instant = [self._instant_ticket(item) for item in instant_rows]
        merged = sorted(
            regular + instant,
            key=lambda item: (item.scheduled_at, item.public_number),
            reverse=True,
        )
        return tuple(merged[offset : offset + limit])

    async def ticket_count(
        self,
        user_id: UUID,
        *,
        active: bool,
        lottery_code: str | None = None,
        wins_only: bool = False,
        scope: LotteryScope = "all",
    ) -> int:
        only_instant = lottery_code in INSTANT_GAMES
        filters = [Ticket.user_id == user_id, lottery_scope(scope)]
        if active:
            filters.append(Ticket.status == TicketStatus.PURCHASED)
        else:
            filters.append(
                Ticket.status.in_((TicketStatus.SETTLED, TicketStatus.REFUNDED))
            )
        if lottery_code and not only_instant:
            filters.append(Lottery.code == lottery_code)
        if wins_only:
            filters.append(Ticket.prize_amount > 0)
        regular_count = (
            0
            if only_instant
            else int(
                await self._session.scalar(
                    select(func.count(Ticket.id))
                    .join(Lottery, Lottery.id == Ticket.lottery_id)
                    .where(*filters)
                )
                or 0
            )
        )
        instant_count = 0
        if not active and ((not lottery_code and scope == "all") or only_instant):
            instant_filters = [InstantTicket.user_id == user_id]
            if only_instant and lottery_code:
                instant_filters.append(
                    InstantTicket.odds_version.in_(instant_versions(lottery_code))
                )
            if wins_only:
                instant_filters.append(InstantTicket.prize_amount > 0)
            instant_count = int(
                await self._session.scalar(
                    select(func.count(InstantTicket.id)).where(*instant_filters)
                )
                or 0
            )
        return regular_count + instant_count

    async def results(self, *, limit: int = 50) -> tuple[MiniAppDrawResult, ...]:
        rows = (
            await self._session.execute(
                select(Draw, Lottery)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .where(Draw.status == DrawStatus.COMPLETED)
                .order_by(Draw.scheduled_at.desc())
                .limit(limit)
            )
        ).all()
        return tuple(
            MiniAppDrawResult(
                lottery.code,
                draw_display_name(lottery.code, lottery.name, draw.scheduled_at),
                draw.public_number,
                draw.scheduled_at,
                draw.executed_at,
                tuple(draw.winning_numbers or ()),
                draw.ticket_count,
                draw.total_payout,
            )
            for draw, lottery in rows
        )

    async def live(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
        fast_only: bool = False,
        lottery_code: str | None = None,
    ) -> MiniAppLiveFeed:
        timestamp = now or datetime.now(UTC)

        async def load() -> PublicLiveFeed:
            return await self._public_live(timestamp, fast_only, lottery_code)

        bind = getattr(self._session, "bind", None)
        if isinstance(bind, AsyncEngine) and now is None:
            cache = _live_caches.setdefault(bind, DisplayCache(seconds=2))
            public = await cache.get((fast_only, lottery_code), load)
        else:
            public = await load()
        contexts = public.recent + ((public.upcoming,) if public.upcoming else ())
        personal = await self._personal_live(user_id, contexts, timestamp)
        recent = tuple(personal[item.draw_id] for item in public.recent)
        return MiniAppLiveFeed(
            server_time=timestamp,
            latest_completed=recent[0] if recent else None,
            next_scheduled=personal[public.upcoming.draw_id]
            if public.upcoming
            else None,
            recent_completed=recent,
        )

    async def _public_live(
        self,
        timestamp: datetime,
        fast_only: bool,
        lottery_code: str | None,
    ) -> PublicLiveFeed:
        lottery_filter: ColumnElement[bool] = (
            Lottery.code.in_(FAST_LOTTERY_CODES)
            if fast_only
            else Lottery.code.not_in((*FAST_LOTTERY_CODES, "bingo"))
        )
        if lottery_code:
            lottery_filter = lottery_filter & (Lottery.code == lottery_code)
        completed_rows = (
            await self._session.execute(
                select(Draw, Lottery, JackpotAccount.balance)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .outerjoin(JackpotAccount, JackpotAccount.lottery_id == Lottery.id)
                .where(
                    Draw.status == DrawStatus.COMPLETED,
                    lottery_filter,
                )
                .order_by(Draw.scheduled_at.desc())
                .limit(50)
            )
        ).all()
        recent_rows: list[tuple[Draw, Lottery, int | None]] = []
        per_lottery: dict[str, int] = {}
        for row in completed_rows:
            display_code = draw_display_code(row[1].code, row[0].scheduled_at)
            if per_lottery.get(display_code, 0) >= 2:
                continue
            recent_rows.append((row[0], row[1], row[2]))
            per_lottery[display_code] = per_lottery.get(display_code, 0) + 1
        active_statuses = (
            (
                DrawStatus.SCHEDULED,
                DrawStatus.CLOSED,
                DrawStatus.DRAWING,
                DrawStatus.SETTLING,
            )
            if fast_only
            else (DrawStatus.SCHEDULED,)
        )
        next_statement = (
            select(Draw, Lottery, JackpotAccount.balance)
            .join(Lottery, Lottery.id == Draw.lottery_id)
            .outerjoin(JackpotAccount, JackpotAccount.lottery_id == Lottery.id)
            .where(Draw.status.in_(active_statuses), lottery_filter)
        )
        if fast_only:
            next_statement = next_statement.where(
                Draw.scheduled_at >= timestamp - timedelta(minutes=2)
            )
        next_row = (
            await self._session.execute(
                next_statement.order_by(Draw.scheduled_at, Draw.public_number).limit(1)
            )
        ).first()
        recent = tuple(
            PublicLiveDraw(
                draw.id,
                lottery.code,
                self._public_live_draw(draw, lottery, jackpot, timestamp),
            )
            for draw, lottery, jackpot in recent_rows
        )
        upcoming = (
            PublicLiveDraw(
                next_row[0].id,
                next_row[1].code,
                self._public_live_draw(
                    next_row[0], next_row[1], next_row[2], timestamp
                ),
            )
            if next_row
            else None
        )
        return PublicLiveFeed(recent, upcoming)

    @staticmethod
    def _public_live_draw(
        draw: Draw,
        lottery: Lottery,
        jackpot: int | None,
        now: datetime,
    ) -> MiniAppLiveDraw:
        timeline_factory = (
            fast_presentation_timeline
            if lottery.code in FAST_LOTTERY_CODES
            else khan_presentation_timeline
            if lottery.code == "khan"
            else presentation_timeline
        )
        timeline = timeline_factory(
            draw.scheduled_at,
            draw.executed_at if draw.status == DrawStatus.COMPLETED else None,
            2 if lottery.code == "dual" else lottery.numbers_to_pick,
        )
        snapshot = draw.configuration_snapshot or {}
        rules = get_lottery_rules(
            str(snapshot.get("ruleset_code", lottery.ruleset_code))
        )
        return MiniAppLiveDraw(
            lottery_code=draw_display_code(lottery.code, draw.scheduled_at),
            lottery_name=draw_display_name(
                lottery.code, lottery.name, draw.scheduled_at
            ),
            lottery_kind=lottery.kind,
            draw_number=draw.public_number,
            scheduled_at=draw.scheduled_at,
            status=draw.status,
            winning_numbers=(
                tuple(draw.winning_numbers) if draw.winning_numbers else None
            ),
            jackpot=jackpot or 0,
            player_ticket_count=0,
            player_winning_ticket_count=0,
            player_best_matches=None,
            player_total_prize=0,
            highlighted_tickets=(),
            sales_close_at=draw.sales_close_at,
            sales_status=sales_status(
                now=now,
                status=draw.status,
                sales_close_at=draw.sales_close_at,
                timeline=timeline,
            ),
            live_starts_at=timeline.starts_at,
            reveal_at=timeline.reveal_at,
            live_ends_at=timeline.ends_at,
            primary_numbers_to_pick=rules.display_primary_numbers_to_pick,
            secondary_storage_offset=rules.secondary_storage_offset,
            primary_max_number=rules.display_primary_max_number,
            is_distribution=bool(draw.is_distribution),
        )

    async def _live_draw(
        self,
        user_id: UUID,
        draw: Draw,
        lottery: Lottery,
        jackpot: int | None,
    ) -> MiniAppLiveDraw:
        now = datetime.now(UTC)
        context = PublicLiveDraw(
            draw.id, lottery.code, self._public_live_draw(draw, lottery, jackpot, now)
        )
        return (await self._personal_live(user_id, (context,), now))[draw.id]

    async def _personal_live(
        self,
        user_id: UUID,
        contexts: tuple[PublicLiveDraw, ...],
        now: datetime,
    ) -> dict[UUID, MiniAppLiveDraw]:
        if not contexts:
            return {}
        ids = [item.draw_id for item in contexts]
        dual_ids = [item.draw_id for item in contexts if item.code == "dual"]
        links = union_all(
            select(Ticket.id.label("ticket_id"), Ticket.draw_id.label("live_id")).where(
                Ticket.user_id == user_id, Ticket.draw_id.in_(ids)
            ),
            select(
                Ticket.id.label("ticket_id"), Ticket.second_draw_id.label("live_id")
            ).where(Ticket.user_id == user_id, Ticket.second_draw_id.in_(dual_ids)),
        ).subquery()
        aggregates = (
            await self._session.execute(
                select(
                    links.c.live_id,
                    func.count(Ticket.id),
                    func.count(Ticket.id).filter(Ticket.prize_amount > 0),
                    func.max(Ticket.matches),
                    func.coalesce(func.sum(Ticket.prize_amount), 0),
                )
                .join(Ticket, Ticket.id == links.c.ticket_id)
                .group_by(links.c.live_id)
            )
        ).all()
        totals = {row[0]: row[1:] for row in aggregates}
        revealing = {
            item.draw_id: item
            for item in contexts
            if item.code == "khan"
            and item.value.status == DrawStatus.COMPLETED
            and item.value.live_starts_at <= now < item.value.live_ends_at
        }
        completed = [
            item.draw_id
            for item in contexts
            if item.value.status == DrawStatus.COMPLETED
            and item.draw_id in totals
            and item.draw_id not in revealing
        ]
        highlighted: dict[UUID, list[MiniAppLiveTicket]] = {}
        if completed:
            ranked = (
                select(
                    links.c.live_id,
                    Ticket.public_number,
                    Ticket.numbers,
                    Ticket.matches,
                    Ticket.prize_amount,
                    func.row_number()
                    .over(
                        partition_by=links.c.live_id,
                        order_by=(
                            Ticket.prize_amount.desc(),
                            Ticket.matches.desc().nullslast(),
                            Ticket.public_number,
                        ),
                    )
                    .label("rank"),
                )
                .join(Ticket, Ticket.id == links.c.ticket_id)
                .where(links.c.live_id.in_(completed))
                .subquery()
            )
            rows = (
                await self._session.execute(
                    select(ranked)
                    .where(ranked.c.rank <= 3)
                    .order_by(ranked.c.live_id, ranked.c.rank)
                )
            ).all()
            for row in rows:
                highlighted.setdefault(row.live_id, []).append(
                    MiniAppLiveTicket(
                        row.public_number,
                        tuple(row.numbers),
                        row.matches,
                        row.prize_amount,
                    )
                )
        for identifier, item in revealing.items():
            revealed_count = sum(moment <= now for moment in item.value.reveal_at)
            if not revealed_count or identifier not in totals:
                continue
            revealed = set((item.value.winning_numbers or ())[:revealed_count])
            if not revealed:
                continue
            partial_matches = sum(
                (
                    case((Ticket.numbers.contains([number]), 1), else_=0)
                    for number in revealed
                ),
                start=literal(0),
            )
            tickets = (
                await self._session.scalars(
                    select(Ticket)
                    .where(Ticket.user_id == user_id, Ticket.draw_id == identifier)
                    .order_by(partial_matches.desc(), Ticket.public_number)
                    .limit(1)
                )
            ).all()
            if tickets:
                best = max(
                    tickets,
                    key=lambda ticket: (
                        len(revealed.intersection(ticket.numbers)),
                        -ticket.public_number,
                    ),
                )
                highlighted[identifier] = [
                    MiniAppLiveTicket(
                        best.public_number,
                        tuple(best.numbers),
                        len(revealed.intersection(best.numbers)),
                        0,
                    )
                ]
        return {
            item.draw_id: replace(
                item.value,
                player_ticket_count=int(totals.get(item.draw_id, (0, 0, None, 0))[0]),
                player_winning_ticket_count=int(
                    totals.get(item.draw_id, (0, 0, None, 0))[1]
                ),
                player_best_matches=totals.get(item.draw_id, (0, 0, None, 0))[2],
                player_total_prize=int(totals.get(item.draw_id, (0, 0, None, 0))[3]),
                highlighted_tickets=tuple(highlighted.get(item.draw_id, [])),
            )
            for item in contexts
        }

    async def activity(
        self, user_id: UUID, *, limit: int = 100
    ) -> tuple[PlayerActivity, ...]:
        rows = (
            await self._session.execute(
                select(LedgerTransaction, Lottery.name)
                .outerjoin(Lottery, Lottery.id == LedgerTransaction.lottery_id)
                .where(
                    LedgerTransaction.user_id == user_id,
                    LedgerTransaction.account_kind == LedgerAccountKind.USER_BALANCE,
                )
                .order_by(LedgerTransaction.created_at.desc())
                .limit(limit)
            )
        ).all()
        return tuple(
            PlayerActivity(
                transaction.type,
                transaction.amount,
                transaction.balance_after,
                lottery_name,
                transaction.created_at,
                transaction.details,
            )
            for transaction, lottery_name in rows
        )
