"""Telegram gameplay read models built on immutable platform history."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.enums import (
    DrawStatus,
    LedgerAccountKind,
    TicketStatus,
    TransactionType,
)
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    JackpotAccount,
    LedgerTransaction,
    Lottery,
    Ticket,
    User,
)


@dataclass(frozen=True, slots=True)
class BotPlayer:
    id: UUID
    display_name: str
    balance: int


@dataclass(frozen=True, slots=True)
class BotLotteryCard:
    id: UUID
    code: str
    name: str
    numbers_to_pick: int
    max_number: int
    ticket_price: int | None
    jackpot: int
    draw_number: int | None
    scheduled_at: datetime | None
    sales_close_at: datetime | None
    purchase_available: bool


@dataclass(frozen=True, slots=True)
class BotHome:
    player: BotPlayer
    active_ticket_count: int
    lotteries: tuple[BotLotteryCard, ...]


@dataclass(frozen=True, slots=True)
class BotTicket:
    public_number: int
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
class BotDraw:
    lottery_name: str
    public_number: int
    scheduled_at: datetime
    executed_at: datetime | None
    winning_numbers: tuple[int, ...]
    ticket_count: int
    total_sales: int
    total_payout: int
    jackpot_closing: int | None
    distribution_closing: int | None


@dataclass(frozen=True, slots=True)
class BotPlayerStatistics:
    ticket_count: int
    spent: int
    won: int
    net: int
    best_prize: int
    best_matches: int
    match_counts: dict[int, int]


class TelegramGameplayQueryService:
    """Supply Telegram views without embedding SQL or rules in handlers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def player(self, telegram_id: int) -> BotPlayer:
        row = (
            await self._session.execute(
                select(User, Balance.amount)
                .join(Balance, Balance.user_id == User.id)
                .where(
                    User.telegram_id == telegram_id,
                    User.is_active.is_(True),
                    User.is_admin.is_(False),
                )
            )
        ).one_or_none()
        if row is None:
            raise LookupError("Telegram player is not registered.")
        user, balance = row
        return BotPlayer(user.id, user.display_name, balance)

    async def home(self, telegram_id: int, *, now: datetime) -> BotHome:
        player = await self.player(telegram_id)
        active_count = await self._session.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.user_id == player.id,
                Ticket.status == TicketStatus.PURCHASED,
            )
        )
        rows = (
            await self._session.execute(
                select(Lottery, JackpotAccount.balance)
                .outerjoin(JackpotAccount, JackpotAccount.lottery_id == Lottery.id)
                .where(Lottery.is_active.is_(True))
                .order_by(Lottery.code)
            )
        ).all()
        cards: list[BotLotteryCard] = []
        for lottery, jackpot in rows:
            draw = await self._session.scalar(
                select(Draw)
                .where(
                    Draw.lottery_id == lottery.id,
                    Draw.status == DrawStatus.SCHEDULED,
                    Draw.sales_close_at > now,
                )
                .order_by(Draw.scheduled_at)
                .limit(1)
            )
            cards.append(
                BotLotteryCard(
                    lottery.id,
                    lottery.code,
                    lottery.name,
                    lottery.numbers_to_pick,
                    lottery.max_number,
                    lottery.ticket_price,
                    jackpot or 0,
                    draw.public_number if draw else None,
                    draw.scheduled_at if draw else None,
                    draw.sales_close_at if draw else None,
                    lottery.ticket_price is not None and draw is not None,
                )
            )
        return BotHome(player, active_count or 0, tuple(cards))

    async def tickets(
        self, telegram_id: int, *, active: bool, limit: int = 10
    ) -> tuple[BotTicket, ...]:
        player = await self.player(telegram_id)
        ticket_status = TicketStatus.PURCHASED if active else TicketStatus.SETTLED
        rows = (
            await self._session.execute(
                select(Ticket, Draw, Lottery)
                .join(Draw, Draw.id == Ticket.draw_id)
                .join(Lottery, Lottery.id == Ticket.lottery_id)
                .where(Ticket.user_id == player.id, Ticket.status == ticket_status)
                .order_by(Draw.scheduled_at.desc(), Ticket.public_number.desc())
                .limit(limit)
            )
        ).all()
        return tuple(
            BotTicket(
                ticket.public_number,
                lottery.name,
                draw.public_number,
                draw.scheduled_at,
                tuple(ticket.numbers),
                ticket.purchase_price,
                ticket.status,
                ticket.matches,
                ticket.prize_amount,
                tuple(draw.winning_numbers) if draw.winning_numbers else None,
            )
            for ticket, draw, lottery in rows
        )

    async def recent_draws(self, *, limit: int = 5) -> tuple[BotDraw, ...]:
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
            BotDraw(
                lottery.name,
                draw.public_number,
                draw.scheduled_at,
                draw.executed_at,
                tuple(draw.winning_numbers or []),
                draw.ticket_count,
                draw.total_sales,
                draw.total_payout,
                draw.jackpot_closing,
                draw.distribution_closing,
            )
            for draw, lottery in rows
        )

    async def statistics(self, telegram_id: int) -> BotPlayerStatistics:
        player = await self.player(telegram_id)
        tickets = (
            await self._session.scalars(
                select(Ticket).where(Ticket.user_id == player.id)
            )
        ).all()
        ledger = (
            await self._session.scalars(
                select(LedgerTransaction).where(
                    LedgerTransaction.user_id == player.id,
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
        settled = [ticket for ticket in tickets if ticket.matches is not None]
        match_counts = {
            count: sum(1 for ticket in settled if ticket.matches == count)
            for count in range(6)
        }
        return BotPlayerStatistics(
            ticket_count=len(tickets),
            spent=spent,
            won=won,
            net=won - spent,
            best_prize=max((ticket.prize_amount for ticket in tickets), default=0),
            best_matches=max((ticket.matches or 0 for ticket in settled), default=0),
            match_counts=match_counts,
        )
