"""Shared public snapshots never share a player's private ticket results."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from k_loto.application.display_cache import DisplayCache
from k_loto.application.miniapp import (
    MiniAppQueryService,
    PublicLiveDraw,
    PublicLiveFeed,
)
from k_loto.domain.enums import DrawStatus, LotteryKind
from k_loto.infrastructure.database.models import Draw, Lottery


def context(code="weekly"):
    now = datetime.now(UTC)
    draw = Draw(
        id=UUID(int=1),
        public_number=7,
        scheduled_at=now,
        executed_at=now,
        sales_close_at=now,
        status=DrawStatus.COMPLETED,
        winning_numbers=[1, 2, 3, 4, 5],
        configuration_snapshot={},
    )
    lottery = Lottery(
        code=code,
        name="Public draw",
        kind=LotteryKind.WEEKLY,
        numbers_to_pick=5,
        ruleset_code="weekly_5_20",
    )
    value = MiniAppQueryService._public_live_draw(draw, lottery, 100, now)
    return PublicLiveDraw(draw.id, code, value)


async def test_many_viewers_share_only_public_work_and_scope_keys(monkeypatch):
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost/test")
    shared = context()
    load = AsyncMock(return_value=PublicLiveFeed((shared,), None))
    monkeypatch.setattr(MiniAppQueryService, "_public_live", load)

    async def personal(self, user_id, contexts, now):
        return {
            item.draw_id: replace(item.value, player_ticket_count=user_id.int)
            for item in contexts
        }

    monkeypatch.setattr(MiniAppQueryService, "_personal_live", personal)
    services = [MiniAppQueryService(SimpleNamespace(bind=engine)) for _ in range(10)]
    feeds = await asyncio.gather(
        *(service.live(UUID(int=i + 1)) for i, service in enumerate(services))
    )
    assert load.await_count == 1
    assert [feed.latest_completed.player_ticket_count for feed in feeds] == list(
        range(1, 11)
    )
    assert shared.value.player_ticket_count == 0
    await services[0].live(UUID(int=1), fast_only=True)
    await services[0].live(UUID(int=1), lottery_code="khan")
    assert load.await_count == 3
    await engine.dispose()


async def test_display_cache_expiry_bound_and_failed_load(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("k_loto.application.display_cache.monotonic", lambda: clock[0])
    cache = DisplayCache(seconds=2, capacity=2)
    load = AsyncMock(side_effect=[1, 2, 3, 4])
    assert await cache.get("a", load) == 1
    assert await cache.get("a", load) == 1
    clock[0] = 2
    assert await cache.get("a", load) == 2
    assert await cache.get("b", load) == 3
    assert await cache.get("c", load) == 4
    assert len(cache.values) == 2 and "a" not in cache.values
    with pytest.raises(RuntimeError):
        await cache.get("failed", AsyncMock(side_effect=RuntimeError))
    assert "failed" not in cache.values
    assert await cache.get("failed", AsyncMock(return_value=5)) == 5


async def test_personal_aggregates_are_batched_and_include_dual_second_round():
    from sqlalchemy.dialects import postgresql

    shared = context("dual")
    statements = []

    async def execute(statement):
        statements.append(
            str(
                statement.compile(
                    dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
                )
            )
        )
        if len(statements) == 1:
            rows = [(shared.draw_id, 2, 1, 4, 100)]
        else:
            rows = [
                SimpleNamespace(
                    live_id=shared.draw_id,
                    public_number=9,
                    numbers=[1, 2],
                    matches=2,
                    prize_amount=100,
                )
            ]
        return SimpleNamespace(all=lambda: rows)

    result = await MiniAppQueryService(SimpleNamespace(execute=execute))._personal_live(
        UUID(int=12), (shared,), datetime.now(UTC)
    )
    assert len(statements) == 2
    assert "second_draw_id IN" in statements[0]
    assert statements[0].count("tickets.user_id =") == 2
    assert "row_number() OVER (PARTITION BY" in statements[1]
    assert "rank <= 3" in statements[1]
    assert result[shared.draw_id].player_ticket_count == 2
    assert result[shared.draw_id].player_total_prize == 100
    assert result[shared.draw_id].highlighted_tickets[0].public_number == 9


async def test_khan_partial_reveal_fetches_only_the_best_owned_ticket():
    from sqlalchemy.dialects import postgresql

    shared = context("khan")
    now = shared.value.reveal_at[0] + timedelta(milliseconds=1)
    aggregate = SimpleNamespace(all=lambda: [(shared.draw_id, 1000, 1, 5, 100)])
    statement = []

    async def scalars(query):
        statement.append(
            str(
                query.compile(
                    dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
                )
            )
        )
        return SimpleNamespace(
            all=lambda: [SimpleNamespace(public_number=10, numbers=[1, 6, 7, 8, 9])]
        )

    service = MiniAppQueryService(
        SimpleNamespace(execute=AsyncMock(return_value=aggregate), scalars=scalars)
    )
    result = (await service._personal_live(UUID(int=12), (shared,), now))[
        shared.draw_id
    ]
    assert len(statement) == 1 and "LIMIT 1" in statement[0]
    assert "tickets.user_id =" in statement[0] and "ORDER BY" in statement[0]
    assert result.highlighted_tickets[0].matches == 1
    assert result.highlighted_tickets[0].prize_amount == 0
