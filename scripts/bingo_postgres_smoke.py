"""Focused transactional Bingo smoke; exclusively for a disposable database."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

from k_loto.application.bingo import BingoQueryService
from k_loto.application.miniapp import MiniAppQueryService
from k_loto.application.scheduler import DrawScheduleService
from k_loto.application.weekly import (
    LotterySettlementService,
    LotteryTicketPurchaseService,
)
from k_loto.core.config import get_settings
from k_loto.domain import bingo
from k_loto.domain.enums import DrawStatus
from k_loto.domain.errors import InvalidTicket, NoAvailableDraw
from k_loto.infrastructure.database.models import (
    Balance,
    BingoPoolTicket,
    Draw,
    JackpotAccount,
    JackpotWinEvent,
    LedgerTransaction,
    Lottery,
    Ticket,
    User,
)
from k_loto.infrastructure.database.session import engine, session_factory


async def main() -> None:
    database = str(get_settings().database_url).rsplit("/", 1)[-1]
    if not database.startswith("k_loto_bingo_smoke_"):
        raise RuntimeError("This smoke requires a disposable Bingo database.")
    now = datetime.now(UTC)
    users = [uuid4(), uuid4()]
    async with session_factory() as session, session.begin():
        lottery = (
            await session.scalars(select(Lottery).where(Lottery.code == "bingo"))
        ).one()
        lottery_id = lottery.id
        session.add_all([User(id=u, display_name="Bingo smoke") for u in users])
        await session.flush()
        session.add_all([Balance(user_id=u, amount=100_000_000) for u in users])
    async with session_factory() as session:
        draw, _ = await DrawScheduleService(session).ensure_next_draw(
            lottery_id, reference=now
        )
        draw_id = draw.id
    async with session_factory() as session:
        inventory = await BingoQueryService(session).inventory()
        assert inventory["draw_id"] == str(draw_id)
    async with session_factory() as session:
        pool = list(
            (
                await session.scalars(
                    select(BingoPoolTicket)
                    .where(BingoPoolTicket.draw_id == draw_id)
                    .order_by(BingoPoolTicket.public_number)
                )
            ).all()
        )
        assert len(pool) == 2000
        assert len({tuple(sorted(t.numbers)) for t in pool}) == 2000

    async def buy(user, entries, key):
        async with session_factory() as session:
            return await LotteryTicketPurchaseService(
                session, "bingo", draw_id
            ).purchase(
                user_id=user,
                combinations=[[] for _ in entries],
                pool_ticket_ids=entries,
                idempotency_key=key,
            )

    contest = await asyncio.gather(
        *[buy(u, [pool[0].id], f"bingo-contest-{u}") for u in users],
        return_exceptions=True,
    )
    assert sum(isinstance(r, NoAvailableDraw) for r in contest) == 1, [
        (type(r).__name__, str(r)[:1500]) for r in contest
    ]
    winner = next(
        u for u, r in zip(users, contest, strict=True) if not isinstance(r, Exception)
    )
    first = next(r for r in contest if not isinstance(r, Exception))
    repeat = await buy(winner, [pool[0].id], f"bingo-contest-{winner}")
    assert repeat.already_processed and repeat.ticket_ids == first.ticket_ids
    await buy(winner, [t.id for t in pool[1:50]], "bingo-limit-50")
    try:
        await buy(winner, [pool[50].id], "bingo-limit-51")
    except InvalidTicket:
        pass
    else:
        raise AssertionError("51st ticket was accepted")

    async with session_factory() as session, session.begin():
        draw = await session.get(Draw, draw_id)
        assert draw is not None
        draw.scheduled_at = now - timedelta(seconds=1)
        draw.sales_close_at = now - timedelta(minutes=2)
    sequence = tuple(
        pool[0].numbers + [n for n in range(1, 61) if n not in pool[0].numbers]
    )[:58]
    original = bingo.generate_sequence
    bingo.generate_sequence = lambda: sequence
    try:
        async with session_factory() as session:
            await LotterySettlementService(session).settle(draw_id, now=now)
    finally:
        bingo.generate_sequence = original
    async with session_factory() as session:
        feed = await BingoQueryService(session).feed(winner)
        assert len(feed["draw"]["numbers"]) < 58
        assert all(t["result"] is None for t in feed["draw"]["tickets"])
    async with session_factory() as session:
        tickets = await MiniAppQueryService(session).tickets(
            winner, active=True, lottery_code="bingo"
        )
        assert all(t.winning_numbers is None for t in tickets)
    # Purchases for the next draw during broadcast must remain in its jackpot.
    async with session_factory() as session:
        next_draw, _ = await DrawScheduleService(session).ensure_next_draw(
            lottery_id, reference=now
        )
    async with session_factory() as session:
        next_entry = await session.scalar(
            select(BingoPoolTicket)
            .where(BingoPoolTicket.draw_id == next_draw.id)
            .limit(1)
        )
        assert next_entry is not None
    async with session_factory() as session:
        await LotteryTicketPurchaseService(session, "bingo", next_draw.id).purchase(
            user_id=users[0],
            combinations=[[]],
            pool_ticket_ids=[next_entry.id],
            idempotency_key="bingo-next-draw-during-live",
        )
    async with session_factory() as session:
        result = await LotterySettlementService(session).settle(
            draw_id, now=now + timedelta(seconds=120)
        )
        assert result.winning_numbers == sequence
    async with session_factory() as session:
        result = await LotterySettlementService(session).settle(
            draw_id, now=now + timedelta(seconds=121)
        )
        assert result.already_completed
    async with session_factory() as session:
        entries = list(
            (
                await session.scalars(
                    select(LedgerTransaction).where(
                        LedgerTransaction.draw_id == draw_id
                    )
                )
            ).all()
        )
        assert sum(e.amount for e in entries) == 0
        assert len({e.idempotency_key for e in entries}) == len(entries)
        assert (
            await session.scalar(
                select(func.count(JackpotWinEvent.id)).where(
                    JackpotWinEvent.draw_id == draw_id
                )
            )
            == 1
        )
        purchased = list(
            (
                await session.scalars(select(Ticket).where(Ticket.draw_id == draw_id))
            ).all()
        )
        assert len(purchased) == 50
        jackpot = await session.scalar(
            select(JackpotAccount).where(JackpotAccount.lottery_id == lottery_id)
        )
        assert jackpot and jackpot.balance == 10_000_050_000
        event = await session.scalar(
            select(JackpotWinEvent).where(JackpotWinEvent.draw_id == draw_id)
        )
        assert event and event.jackpot_amount == 10_002_500_000
        assert all(t.bingo_result is not None for t in purchased)
        draw = await session.get(Draw, draw_id)
        assert draw and draw.status == DrawStatus.COMPLETED
    await engine.dispose()
    print(
        "Bingo PostgreSQL: 2000-ticket pool, concurrent claim, retry, "
        "50-ticket limit, hidden sequence, recovery, ledger conservation passed."
    )


if __name__ == "__main__":
    asyncio.run(main())
