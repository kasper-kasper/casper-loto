"""Bingo inventory and a public feed which never exposes future balls."""

import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.bingo import (
    DRAW_MOVES,
    JACKPOT_MOVE,
    KASPER_SET_INVENTORY,
    KASPER_SET_NUMBERS,
    KASPER_SET_SIZE,
    POOL_SIZE,
    TOUR_MOVES,
    TOUR_PRIZES,
    closing_moves,
    generate_ticket,
)
from k_loto.domain.enums import DrawStatus
from k_loto.domain.errors import InvalidTicket, NoAvailableDraw
from k_loto.infrastructure.database.models import BingoPoolTicket, Draw, Lottery, Ticket

_STAGE_CACHE: dict[tuple[UUID, int], list[dict[str, int | None]]] = {}


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
    random = secrets.SystemRandom()
    while len(entries) < POOL_SIZE:
        if len(entries) >= POOL_SIZE - KASPER_SET_INVENTORY:
            remainder = random.sample(
                [n for n in range(1, 61) if n not in KASPER_SET_NUMBERS], 8
            )
            shuffled = random.sample((*KASPER_SET_NUMBERS, *remainder), 12)
            numbers = tuple(
                n for i in range(0, 12, 4) for n in sorted(shuffled[i : i + 4])
            )
        else:
            numbers = generate_ticket()
        identity = tuple(sorted(numbers))
        if identity in seen:
            continue
        seen.add(identity)
        entries.append(
            BingoPoolTicket(
                id=uuid4(),
                draw_id=draw.id,
                pool_position=len(entries) + 1,
                numbers=list(numbers),
            )
        )
    session.add_all(entries)
    await session.flush()


class BingoQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def inventory(
        self, *, offset: int = 0, required_numbers: tuple[int, ...] = ()
    ) -> dict[str, Any]:
        if (
            len(required_numbers) > 5
            or len(set(required_numbers)) != len(required_numbers)
            or any(
                type(number) is not int or not 1 <= number <= 60
                for number in required_numbers
            )
        ):
            raise InvalidTicket(
                "Choose up to five distinct Bingo numbers from 1 to 60."
            )
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
            query = select(BingoPoolTicket).where(
                BingoPoolTicket.draw_id == draw.id,
                BingoPoolTicket.ticket_id.is_(None),
            )
            if required_numbers:
                query = query.where(
                    BingoPoolTicket.numbers.contains(list(required_numbers))
                )
            entries = list(
                (
                    await self.session.scalars(
                        query.order_by(BingoPoolTicket.pool_position)
                        .offset(offset)
                        .limit(7)
                    )
                ).all()
            )
            kasper_set_available = int(
                await self.session.scalar(
                    select(func.count(BingoPoolTicket.id)).where(
                        BingoPoolTicket.draw_id == draw.id,
                        BingoPoolTicket.ticket_id.is_(None),
                        BingoPoolTicket.numbers.contains(list(KASPER_SET_NUMBERS)),
                    )
                )
                or 0
            )
            return {
                "draw_id": str(draw.id),
                "draw_number": draw.public_number,
                "scheduled_at": draw.scheduled_at.isoformat(),
                "price": draw.configuration_snapshot["ticket_price"],
                "has_more": len(entries) > 6,
                "kasper_set_available": kasper_set_available >= KASPER_SET_SIZE,
                "tickets": [
                    {
                        "id": str(t.id),
                        "pool_position": t.pool_position,
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
            "tour_moves": list(TOUR_MOVES),
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
        cache_key = (draw.id, count)
        stages = _STAGE_CACHE.get(cache_key)
        if stages is None:
            all_tickets = list(
                (
                    await self.session.scalars(
                        select(Ticket).where(Ticket.draw_id == draw.id)
                    )
                ).all()
            )
            moves = [
                closing_moves(tuple(ticket.numbers), tuple(sequence))
                for ticket in all_tickets
            ]
            stages = []
            for category, cutoff in enumerate((*TOUR_MOVES, JACKPOT_MOVE)):
                reached = count >= cutoff
                stages.append(
                    {
                        "move": cutoff if reached else None,
                        "winners": (
                            sum(move[category] <= cutoff for move in moves)
                            if reached
                            else 0
                        ),
                    }
                )
            _STAGE_CACHE.clear()
            _STAGE_CACHE[cache_key] = stages
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
