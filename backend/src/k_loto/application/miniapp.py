"""Read models for the Telegram Mini App."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.enums import (
    DrawStatus,
    LedgerAccountKind,
    LotteryKind,
    TicketStatus,
    TransactionType,
)
from k_loto.domain.lotteries import draw_display_name
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
    balance: int
    active_ticket_count: int
    lotteries: tuple[MiniAppLottery, ...]
    recent_results: tuple[MiniAppTicket, ...]


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
                    Draw.status == DrawStatus.SCHEDULED,
                    Draw.sales_close_at > timestamp,
                )
                .order_by(Draw.scheduled_at)
                .limit(1)
            )
            sales_open = draw is not None and draw.sales_close_at > timestamp
            purchase_available = lottery.ticket_price is not None and sales_open
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
                )
            )
        recent_results = await self.tickets(user_id, active=False, limit=3)
        return MiniAppDashboard(
            balance=balance,
            active_ticket_count=active_count or 0,
            lotteries=tuple(lotteries),
            recent_results=recent_results,
        )

    async def tickets(
        self, user_id: UUID, *, active: bool, limit: int = 100
    ) -> tuple[MiniAppTicket, ...]:
        status = TicketStatus.PURCHASED if active else TicketStatus.SETTLED
        rows = (
            await self._session.execute(
                select(Ticket, Draw, Lottery)
                .join(Draw, Draw.id == Ticket.draw_id)
                .join(Lottery, Lottery.id == Ticket.lottery_id)
                .where(Ticket.user_id == user_id, Ticket.status == status)
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
