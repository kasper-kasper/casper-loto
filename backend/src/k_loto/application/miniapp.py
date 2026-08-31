"""Read models for the Telegram Mini App."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.enums import (
    DrawStatus,
    LedgerAccountKind,
    LotteryKind,
    TicketStatus,
    TransactionType,
)
from k_loto.domain.live_timeline import draw_timeline, sales_status
from k_loto.domain.lotteries import draw_display_code, draw_display_name
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    JackpotAccount,
    LedgerTransaction,
    Lottery,
    Ticket,
)


@dataclass(frozen=True, slots=True)
class MiniAppLottery:
    code: str
    name: str
    kind: LotteryKind
    numbers_to_pick: int
    max_number: int
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
    status: TicketStatus
    matches: int | None
    prize_amount: int
    winning_numbers: tuple[int, ...] | None


@dataclass(frozen=True, slots=True)
class MiniAppDashboard:
    server_time: datetime
    balance: int
    active_ticket_count: int
    lotteries: tuple[MiniAppLottery, ...]
    recent_results: tuple[MiniAppTicket, ...]
    monthly_total_payout: int


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


class MiniAppQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
                    Draw.status != DrawStatus.COMPLETED,
                )
                .order_by(Draw.scheduled_at)
                .limit(1)
            )
            sales_open = draw is not None and draw.sales_close_at > timestamp
            purchase_available = lottery.ticket_price is not None and sales_open
            player_ticket_count = 0
            if draw is not None:
                player_ticket_count = int(
                    await self._session.scalar(
                        select(func.count(Ticket.id)).where(
                            Ticket.user_id == user_id,
                            Ticket.draw_id == draw.id,
                            Ticket.status == TicketStatus.PURCHASED,
                        )
                    )
                    or 0
                )
            timeline = (
                draw_timeline(draw.scheduled_at, lottery.numbers_to_pick)
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
                    kind=lottery.kind,
                    numbers_to_pick=lottery.numbers_to_pick,
                    max_number=lottery.max_number,
                    ticket_price=lottery.ticket_price,
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
        return MiniAppDashboard(
            server_time=timestamp,
            balance=balance,
            active_ticket_count=active_count or 0,
            lotteries=tuple(lotteries),
            recent_results=recent_results,
            monthly_total_payout=monthly_total_payout,
        )

    async def tickets(
        self,
        user_id: UUID,
        *,
        active: bool,
        limit: int = 100,
        lottery_code: str | None = None,
        wins_only: bool = False,
    ) -> tuple[MiniAppTicket, ...]:
        status = TicketStatus.PURCHASED if active else TicketStatus.SETTLED
        filters = [Ticket.user_id == user_id, Ticket.status == status]
        if lottery_code:
            filters.append(Lottery.code == lottery_code)
        if wins_only:
            filters.append(Ticket.prize_amount > 0)
        rows = (
            await self._session.execute(
                select(Ticket, Draw, Lottery)
                .join(Draw, Draw.id == Ticket.draw_id)
                .join(Lottery, Lottery.id == Ticket.lottery_id)
                .where(*filters)
                .order_by(Draw.scheduled_at.desc(), Ticket.public_number.desc())
                .limit(limit)
            )
        ).all()
        return tuple(
            MiniAppTicket(
                id=ticket.id,
                public_number=ticket.public_number,
                lottery_code=lottery.code,
                lottery_name=draw_display_name(
                    lottery.code, lottery.name, draw.scheduled_at
                ),
                draw_number=draw.public_number,
                scheduled_at=draw.scheduled_at,
                numbers=tuple(ticket.numbers),
                purchase_price=ticket.purchase_price,
                status=ticket.status,
                matches=ticket.matches,
                prize_amount=ticket.prize_amount,
                winning_numbers=(
                    tuple(draw.winning_numbers) if draw.winning_numbers else None
                ),
            )
            for ticket, draw, lottery in rows
        )

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
        self, user_id: UUID, *, now: datetime | None = None
    ) -> MiniAppLiveFeed:
        """Return immutable draw facts and a server clock for visual playback."""
        timestamp = now or datetime.now(UTC)
        completed_rows = (
            await self._session.execute(
                select(Draw, Lottery, JackpotAccount.balance)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .outerjoin(JackpotAccount, JackpotAccount.lottery_id == Lottery.id)
                .where(Draw.status == DrawStatus.COMPLETED)
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
        next_row = (
            await self._session.execute(
                select(Draw, Lottery, JackpotAccount.balance)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .outerjoin(JackpotAccount, JackpotAccount.lottery_id == Lottery.id)
                .where(Draw.status == DrawStatus.SCHEDULED)
                .order_by(Draw.scheduled_at, Draw.public_number)
                .limit(1)
            )
        ).first()
        return MiniAppLiveFeed(
            server_time=timestamp,
            latest_completed=(
                await self._live_draw(
                    user_id, latest_row[0], latest_row[1], latest_row[2]
                )
                if latest_row
                else None
            ),
            next_scheduled=(
                await self._live_draw(user_id, next_row[0], next_row[1], next_row[2])
                if next_row
                else None
            ),
            recent_completed=tuple(
                [
                    await self._live_draw(user_id, draw, lottery, jackpot)
                    for draw, lottery, jackpot in recent_rows
                ]
            ),
        )

    async def _live_draw(
        self,
        user_id: UUID,
        draw: Draw,
        lottery: Lottery,
        jackpot: int | None,
    ) -> MiniAppLiveDraw:
        aggregate = (
            await self._session.execute(
                select(
                    func.count(Ticket.id),
                    func.count(Ticket.id).filter(Ticket.prize_amount > 0),
                    func.max(Ticket.matches),
                    func.coalesce(func.sum(Ticket.prize_amount), 0),
                ).where(Ticket.user_id == user_id, Ticket.draw_id == draw.id)
            )
        ).one()
        highlighted: tuple[MiniAppLiveTicket, ...] = ()
        if draw.status == DrawStatus.COMPLETED and aggregate[0]:
            tickets = (
                await self._session.execute(
                    select(Ticket)
                    .where(Ticket.user_id == user_id, Ticket.draw_id == draw.id)
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
                for ticket in tickets
            )
        timeline = draw_timeline(draw.scheduled_at, lottery.numbers_to_pick)
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
                now=datetime.now(UTC),
                status=draw.status,
                sales_close_at=draw.sales_close_at,
                timeline=timeline,
            ),
            live_starts_at=timeline.starts_at,
            reveal_at=timeline.reveal_at,
            live_ends_at=timeline.ends_at,
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
