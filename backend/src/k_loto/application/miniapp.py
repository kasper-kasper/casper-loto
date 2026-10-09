"""Read models for the Telegram Mini App."""

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from k_loto.application.query_scope import LotteryScope, lottery_scope
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
    instant_rules,
    instant_rules_for_version,
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
    Ticket,
    User,
    UserNotification,
    UserNotificationPreference,
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
                        Draw.status != DrawStatus.COMPLETED,
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
        user = await self._session.get(User, user_id)
        if user is None:
            raise LookupError("Player does not exist.")
        balance = int(
            await self._session.scalar(
                select(Balance.amount).where(Balance.user_id == user_id)
            )
            or 0
        )
        stats = (
            await self._session.execute(
                select(
                    func.count(Ticket.id),
                    func.count(Ticket.id).filter(
                        Ticket.status == TicketStatus.PURCHASED
                    ),
                    func.count(Ticket.id).filter(Ticket.prize_amount > 0),
                    func.coalesce(
                        func.sum(Ticket.purchase_price).filter(
                            Ticket.status != TicketStatus.REFUNDED
                        ),
                        0,
                    ),
                    func.coalesce(func.sum(Ticket.prize_amount), 0),
                    func.coalesce(func.max(Ticket.prize_amount), 0),
                ).where(Ticket.user_id == user_id)
            )
        ).one()
        instant_stats = (
            await self._session.execute(
                select(
                    func.count(InstantTicket.id),
                    func.count(InstantTicket.id).filter(InstantTicket.prize_amount > 0),
                    func.coalesce(func.sum(InstantTicket.purchase_price), 0),
                    func.coalesce(func.sum(InstantTicket.prize_amount), 0),
                    func.coalesce(func.max(InstantTicket.prize_amount), 0),
                ).where(InstantTicket.user_id == user_id)
            )
        ).one()
        preference = await self._session.get(UserNotificationPreference, user_id)
        unread = int(
            await self._session.scalar(
                select(func.count(UserNotification.id)).where(
                    UserNotification.user_id == user_id,
                    UserNotification.read_at.is_(None),
                    UserNotification.type != InAppNotificationType.DRAW_RESULT,
                )
            )
            or 0
        )
        favorite_lottery = (
            await self._session.execute(
                select(Lottery.code, Lottery.name, func.count(Ticket.id).label("uses"))
                .join(Ticket, Ticket.lottery_id == Lottery.id)
                .where(
                    Ticket.user_id == user_id,
                    Ticket.status != TicketStatus.REFUNDED,
                )
                .group_by(Lottery.id)
                .order_by(func.count(Ticket.id).desc(), Lottery.code)
                .limit(1)
            )
        ).first()
        favorite_numbers: tuple[int, ...] = ()
        if favorite_lottery is not None:
            number_rows = await self._session.scalars(
                select(Ticket.numbers).where(
                    Ticket.user_id == user_id,
                    Ticket.lottery_id
                    == select(Lottery.id)
                    .where(Lottery.code == favorite_lottery.code)
                    .scalar_subquery(),
                    Ticket.status != TicketStatus.REFUNDED,
                )
            )
            counts = Counter(number for numbers in number_rows for number in numbers)
            favorite_numbers = tuple(number for number, _ in counts.most_common(7))
        return MiniAppAccount(
            display_name=user.display_name,
            balance=balance,
            ticket_count=int(stats[0]) + int(instant_stats[0]),
            active_ticket_count=int(stats[1]),
            winning_ticket_count=int(stats[2]) + int(instant_stats[1]),
            total_spent=int(stats[3]) + int(instant_stats[2]),
            total_won=int(stats[4]) + int(instant_stats[3]),
            best_win=max(int(stats[5]), int(instant_stats[4])),
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
            unread_notification_count=unread,
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
        self, user_id: UUID, *, now: datetime | None = None
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
        lotteries: list[MiniAppLottery] = []
        for lottery, jackpot in lottery_rows:
            draw = await self._session.scalar(
                select(Draw)
                .where(
                    Draw.lottery_id == lottery.id,
                    Draw.status == DrawStatus.SCHEDULED,
                    Draw.scheduled_at > timestamp,
                    Draw.sales_close_at > timestamp,
                )
                .order_by(Draw.scheduled_at)
                .limit(1)
            )
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
            player_ticket_count = 0
            if draw is not None:
                player_ticket_count = int(
                    await self._session.scalar(
                        select(func.count(Ticket.id)).where(
                            Ticket.user_id == user_id,
                            or_(
                                Ticket.draw_id == draw.id,
                                Ticket.second_draw_id == draw.id,
                            )
                            if lottery.code == "dual"
                            else Ticket.draw_id == draw.id,
                            Ticket.status == TicketStatus.PURCHASED,
                        )
                    )
                    or 0
                )
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
        recent_results = await self.tickets(user_id, active=False, limit=3)
        moscow_now = timestamp.astimezone(ZoneInfo("Europe/Moscow"))
        month_start_local = moscow_now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        month_start = month_start_local.astimezone(UTC)
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
        return MiniAppDashboard(
            server_time=timestamp,
            balance=balance,
            active_ticket_count=active_count or 0,
            lotteries=tuple(lotteries),
            recent_results=recent_results,
            monthly_total_payout=monthly_total_payout,
            total_ticket_count=int(ticket_totals[0]) + int(instant_ticket_totals[0]),
            total_winning_ticket_count=int(ticket_totals[1])
            + int(instant_ticket_totals[1]),
        )

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
            regular_rows = (
                await self._session.execute(
                    select(
                        Ticket,
                        Draw,
                        second_draw,
                        Lottery,
                        func.count(Ticket.id).over(partition_by=Ticket.draw_id),
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
                MiniAppTicket(
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
                        and (
                            lottery.code != "bingo"
                            or draw.status == DrawStatus.COMPLETED
                        )
                        else None
                    ),
                    draw_ticket_count=int(draw_ticket_count),
                    bingo_result=ticket.bingo_result,
                    primary_max_number=(
                        16
                        if lottery.code == "grob"
                        and ticket.status == TicketStatus.REFUNDED
                        else int(
                            (draw.configuration_snapshot or {}).get(
                                "max_number", lottery.max_number
                            )
                        )
                        if lottery.code == "grob"
                        else None
                    ),
                    second_draw_number=second.public_number
                    if second is not None
                    else None,
                    second_scheduled_at=second.scheduled_at
                    if second is not None
                    else None,
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
                for ticket, draw, second, lottery, draw_ticket_count in regular_rows
            ]
        if not include_instant:
            return tuple(regular)
        instant_filters = [InstantTicket.user_id == user_id]
        if only_instant and lottery_code:
            instant_filters.append(
                InstantTicket.odds_version == instant_rules(lottery_code).version
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
        instant = [
            MiniAppTicket(
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
            for item in instant_rows
        ]
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
                    InstantTicket.odds_version == instant_rules(lottery_code).version
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
        """Return immutable draw facts and a server clock for visual playback."""
        timestamp = now or datetime.now(UTC)
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
            lottery_code = draw_display_code(row[1].code, row[0].scheduled_at)
            if per_lottery.get(lottery_code, 0) >= 2:
                continue
            recent_rows.append((row[0], row[1], row[2]))
            per_lottery[lottery_code] = per_lottery.get(lottery_code, 0) + 1
        latest_row = recent_rows[0] if recent_rows else None
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
        recent_draws = tuple(
            [
                await self._live_draw(user_id, draw, lottery, jackpot)
                for draw, lottery, jackpot in recent_rows
            ]
        )
        return MiniAppLiveFeed(
            server_time=timestamp,
            latest_completed=recent_draws[0] if latest_row else None,
            next_scheduled=(
                await self._live_draw(user_id, next_row[0], next_row[1], next_row[2])
                if next_row
                else None
            ),
            recent_completed=recent_draws,
        )

    async def _live_draw(
        self,
        user_id: UUID,
        draw: Draw,
        lottery: Lottery,
        jackpot: int | None,
    ) -> MiniAppLiveDraw:
        round_ticket_filter = (
            or_(Ticket.draw_id == draw.id, Ticket.second_draw_id == draw.id)
            if lottery.code == "dual"
            else Ticket.draw_id == draw.id
        )
        aggregate = (
            await self._session.execute(
                select(
                    func.count(Ticket.id),
                    func.count(Ticket.id).filter(Ticket.prize_amount > 0),
                    func.max(Ticket.matches),
                    func.coalesce(func.sum(Ticket.prize_amount), 0),
                ).where(Ticket.user_id == user_id, round_ticket_filter)
            )
        ).one()
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
        presentation_now = datetime.now(UTC)
        highlighted: tuple[MiniAppLiveTicket, ...] = ()
        if draw.status == DrawStatus.COMPLETED and aggregate[0]:
            khan_is_revealing = (
                lottery.code == "khan"
                and timeline.starts_at <= presentation_now < timeline.ends_at
            )
            if khan_is_revealing:
                revealed_count = sum(
                    moment <= presentation_now for moment in timeline.reveal_at
                )
                if revealed_count and draw.winning_numbers:
                    tickets = list(
                        (
                            await self._session.execute(
                                select(Ticket)
                                .where(
                                    Ticket.user_id == user_id,
                                    Ticket.draw_id == draw.id,
                                )
                                .order_by(Ticket.public_number)
                            )
                        ).scalars()
                    )
                    revealed = set(draw.winning_numbers[:revealed_count])
                    best = max(
                        tickets,
                        key=lambda ticket: (
                            len(revealed.intersection(ticket.numbers)),
                            -ticket.public_number,
                        ),
                    )
                    highlighted = (
                        MiniAppLiveTicket(
                            public_number=best.public_number,
                            numbers=tuple(best.numbers),
                            matches=len(revealed.intersection(best.numbers)),
                            prize_amount=0,
                        ),
                    )
            else:
                ranked_tickets = (
                    await self._session.execute(
                        select(Ticket)
                        .where(Ticket.user_id == user_id, round_ticket_filter)
                        .order_by(
                            Ticket.prize_amount.desc(),
                            Ticket.matches.desc().nullslast(),
                            Ticket.public_number,
                        )
                        .limit(3)
                    )
                ).scalars()
                highlighted = tuple(
                    MiniAppLiveTicket(
                        public_number=ticket.public_number,
                        numbers=tuple(ticket.numbers),
                        matches=ticket.matches,
                        prize_amount=ticket.prize_amount,
                    )
                    for ticket in ranked_tickets
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
            player_ticket_count=int(aggregate[0]),
            player_winning_ticket_count=int(aggregate[1]),
            player_best_matches=aggregate[2],
            player_total_prize=int(aggregate[3]),
            highlighted_tickets=highlighted,
            sales_close_at=draw.sales_close_at,
            sales_status=sales_status(
                now=presentation_now,
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
