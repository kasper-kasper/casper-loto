"""Read/purchase concurrency regression on a disposable production backup only."""

import asyncio
import json
from time import perf_counter
from uuid import uuid4

from sqlalchemy import func, select, text

from k_loto.application.identity import TelegramIdentityService
from k_loto.application.miniapp import MiniAppQueryService
from k_loto.application.weekly import LotteryTicketPurchaseService
from k_loto.core.config import get_settings
from k_loto.domain.errors import InvalidTicket
from k_loto.infrastructure.database.models import (
    Balance,
    LedgerTransaction,
    Ticket,
)
from k_loto.infrastructure.database.session import engine, session_factory


async def main():
    assert (
        str(get_settings().database_url)
        .rstrip("/")
        .endswith("/k_loto_performance_smoke")
    )
    async with session_factory() as s:
        original = await s.scalar(
            text(
                "SELECT md5(string_agg(row_to_json(t)::text, '' ORDER BY id)) "
                "FROM tickets t"
            )
        )
        old_draws = await s.scalar(
            text(
                "SELECT md5(string_agg(row_to_json(t)::text, '' ORDER BY id)) "
                "FROM draws t WHERE status='COMPLETED'"
            )
        )
        uid = await s.scalar(
            select(Ticket.user_id)
            .group_by(Ticket.user_id)
            .order_by(func.count().desc())
            .limit(1)
        )
    samples = []
    for _ in range(4):
        async with session_factory() as s:
            start = perf_counter()
            data = await MiniAppQueryService(s).dashboard(
                uid, include_recent_results=False
            )
            samples.append(round((perf_counter() - start) * 1000, 1))
            assert not data.recent_results
            for lottery in data.lotteries:
                if lottery.draw_number is None:
                    continue
                # Count oracle retains the original query's primary/secondary semantics.
                from k_loto.domain.enums import TicketStatus
                from k_loto.infrastructure.database.models import Draw, Lottery

                expected = await s.scalar(
                    select(func.count(Ticket.id))
                    .join(
                        Draw,
                        (Ticket.draw_id == Draw.id)
                        | (Ticket.second_draw_id == Draw.id),
                    )
                    .join(Lottery, Draw.lottery_id == Lottery.id)
                    .where(
                        Ticket.user_id == uid,
                        Ticket.status == TicketStatus.PURCHASED,
                        Lottery.code == lottery.code,
                        Draw.public_number == lottery.draw_number,
                    )
                )
                assert lottery.player_ticket_count == expected
            history = await MiniAppQueryService(s).tickets(uid, active=False, limit=3)
            assert history
            for item in history:
                if item.lottery_code in {"kasper-live", "aurora", "vault"}:
                    continue
                expected = await s.scalar(
                    select(func.count(Ticket.id)).where(
                        Ticket.user_id == uid,
                        Ticket.draw_id
                        == select(Ticket.draw_id)
                        .where(Ticket.id == item.id)
                        .scalar_subquery(),
                        Ticket.status.in_(
                            (TicketStatus.SETTLED, TicketStatus.REFUNDED)
                        ),
                    )
                )
                assert item.draw_ticket_count == expected
    print(json.dumps({"dashboard_ms": samples}), flush=True)

    telegram_id = 8_000_000_000_000 + uuid4().int % 1_000_000_000

    async def bind():
        async with session_factory() as s:
            return await TelegramIdentityService(s).bind(
                telegram_id=telegram_id,
                username=None,
                display_name="Disposable performance fixture",
            )

    identities = await asyncio.gather(bind(), bind())
    player = identities[0].id
    assert identities[1].id == player
    async with session_factory() as s:
        initial = await s.scalar(
            select(Balance.amount).where(Balance.user_id == player)
        )
        assert initial == 100_000_000_000

    async def buy(key):
        async with session_factory() as s:
            return await LotteryTicketPurchaseService(s, lottery_code="khan").purchase(
                user_id=player,
                combinations=[[1, 2, 3, 4, 5, 6]] * 25,
                idempotency_key=key,
            )

    elapsed, receipts = [], []
    for _ in range(8):
        start = perf_counter()
        receipt, _profile = await asyncio.gather(buy(str(uuid4())), bind())
        elapsed.append(round((perf_counter() - start) * 1000, 1))
        receipts.append(receipt)
    key = str(uuid4())
    first, second = await asyncio.gather(buy(key), buy(key))
    assert first.operation_id == second.operation_id
    assert first.ticket_ids == second.ticket_ids and len(first.ticket_ids) == 25
    receipts.append(first)
    async with session_factory() as s:
        try:
            await LotteryTicketPurchaseService(s, lottery_code="khan").purchase(
                user_id=uid, combinations=[[1, 2, 3, 4, 5, 6]], idempotency_key=key
            )
        except InvalidTicket:
            pass
        else:
            raise AssertionError("Cross-user idempotency key was accepted")
    async with session_factory() as s:
        assert (
            await s.scalar(
                select(func.count(Ticket.id)).where(Ticket.user_id == player)
            )
            == 225
        )
        final = await s.scalar(select(Balance.amount).where(Balance.user_id == player))
        assert final == initial - sum(r.total_cost for r in receipts)
        assert final == await s.scalar(
            select(func.sum(LedgerTransaction.amount)).where(
                LedgerTransaction.account_id == player
            )
        )
        remaining = await s.scalar(
            text(
                "SELECT md5(string_agg(row_to_json(t)::text, '' ORDER BY id)) "
                "FROM tickets t WHERE user_id != :uid"
            ),
            {"uid": player},
        )
        assert original == remaining
        assert old_draws == await s.scalar(
            text(
                "SELECT md5(string_agg(row_to_json(t)::text, '' ORDER BY id)) "
                "FROM draws t WHERE status='COMPLETED'"
            )
        )
    print(
        json.dumps(
            {
                "purchase_25_with_identity_ms": elapsed,
                "tickets": 225,
                "duplicate_replay": "passed",
                "ledger": "balanced",
                "existing_history": "unchanged",
            }
        ),
        flush=True,
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
