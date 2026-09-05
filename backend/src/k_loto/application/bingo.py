"""Bingo inventory and a public feed which never exposes future balls."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.bingo import (
    DRAW_MOVES,
    JACKPOT_MOVE,
    POOL_SIZE,
    TOUR_PRIZES,
    closing_moves,
    generate_ticket,
)
from k_loto.domain.enums import DrawStatus
from k_loto.domain.errors import NoAvailableDraw
from k_loto.infrastructure.database.models import BingoPoolTicket, Draw, Lottery, Ticket


async def ensure_pool(session: AsyncSession, lottery: Lottery, draw: Draw) -> None:
    """Caller holds the lottery lock; generate the entire inventory once."""
    existing = await session.scalar(
        select(BingoPoolTicket.id).where(BingoPoolTicket.draw_id == draw.id).limit(1)
    )
    if existing:
        return
    await session.flush()
    seen: set[tuple[int, ...]] = set()
    entries: list[BingoPoolTicket] = []
    while len(entries) < POOL_SIZE:
        numbers = generate_ticket()
        identity = tuple(sorted(numbers))
        if identity in seen:
            continue
        seen.add(identity)
        entries.append(
            BingoPoolTicket(
                id=uuid4(),
                draw_id=draw.id,
                public_number=lottery.next_ticket_number + len(entries),
                numbers=list(numbers),
            )
        )
    lottery.next_ticket_number += POOL_SIZE
    session.add_all(entries)
    await session.flush()


class BingoQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def inventory(self, *, offset: int = 0) -> dict[str, Any]:
        now = datetime.now(UTC)
        async with self.session.begin():
            lottery = await self.session.scalar(
                select(Lottery)
                .where(Lottery.code == "bingo", Lottery.is_active.is_(True))
                .with_for_update()
            )
            if lottery is None:
                raise NoAvailableDraw("Bingo is not available.")
            draw = await self.session.scalar(
                select(Draw)
                .where(
                    Draw.lottery_id == lottery.id,
                    Draw.status == DrawStatus.SCHEDULED,
                    Draw.sales_close_at > now,
                )
                .order_by(Draw.scheduled_at)
                .limit(1)
            )
            if draw is None:
                raise NoAvailableDraw("Bingo sales are closed.")
            await ensure_pool(self.session, lottery, draw)
            entries = list(
                (
                    await self.session.scalars(
                        select(BingoPoolTicket)
                        .where(
                            BingoPoolTicket.draw_id == draw.id,
                            BingoPoolTicket.ticket_id.is_(None),
                        )
                        .order_by(BingoPoolTicket.public_number)
                        .offset(offset)
                        .limit(7)
                    )
                ).all()
            )
            return {
                "draw_id": str(draw.id),
                "draw_number": draw.public_number,
                "scheduled_at": draw.scheduled_at.isoformat(),
                "price": draw.configuration_snapshot["ticket_price"],
                "has_more": len(entries) > 6,
                "tickets": [
                    {
                        "id": str(t.id),
                        "public_number": t.public_number,
                        "numbers": t.numbers,
                    }
                    for t in entries[:6]
                ],
            }

    async def feed(self, user_id: UUID) -> dict[str, Any]:
        now = datetime.now(UTC)
        draw = await self.session.scalar(
            select(Draw)
            .join(Lottery, Lottery.id == Draw.lottery_id)
            .where(Lottery.code == "bingo", Draw.scheduled_at <= now)
            .order_by(Draw.scheduled_at.desc())
            .limit(1)
        )
        rules = {
            "total_moves": DRAW_MOVES,
            "jackpot_move": JACKPOT_MOVE,
            "tour_prizes": list(TOUR_PRIZES),
            "pool_size": POOL_SIZE,
        }
        if draw is None:
            return {"server_time": now.isoformat(), "draw": None, "rules": rules}
        sequence = draw.winning_numbers or []
        started = draw.executed_at
        count = (
            min(len(sequence), max(0, int((now - started).total_seconds() // 2)))
            if started
            else 0
        )
        complete = draw.status == DrawStatus.COMPLETED
        if complete:
            count = len(sequence)
        all_tickets = list(
            (
                await self.session.scalars(
                    select(Ticket).where(Ticket.draw_id == draw.id)
                )
            ).all()
        )
        moves = [closing_moves(tuple(t.numbers), tuple(sequence)) for t in all_tickets]
        stages = []
        for category in range(3):
            first = min((m[category] for m in moves), default=61)
            reached = first <= count and (category != 2 or first <= JACKPOT_MOVE)
            stages.append(
                {
                    "move": first if reached else None,
                    "winners": sum(m[category] == first for m in moves)
                    if reached
                    else 0,
                }
            )
        tickets = list(
            (
                await self.session.scalars(
                    select(Ticket)
                    .where(Ticket.draw_id == draw.id, Ticket.user_id == user_id)
                    .order_by(Ticket.public_number)
                    .limit(50)
                )
            ).all()
        )
        return {
            "server_time": now.isoformat(),
            "rules": rules,
            "draw": {
                "draw_number": draw.public_number,
                "scheduled_at": draw.scheduled_at.isoformat(),
                "complete": complete,
                "numbers": sequence[:count],
                "total_moves": DRAW_MOVES,
                "jackpot_move": JACKPOT_MOVE,
                "tour_prizes": list(TOUR_PRIZES),
                "stages": stages,
                "tickets": [
                    {
                        "id": str(t.id),
                        "public_number": t.public_number,
                        "numbers": t.numbers,
                        "price": t.purchase_price,
                        "result": t.bingo_result if complete else None,
                    }
                    for t in tickets
                ],
            },
        }
