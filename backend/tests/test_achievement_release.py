"""Real PostgreSQL: delayed activation never resets money, history or progress."""

import asyncio
from datetime import UTC, datetime, timedelta
from time import perf_counter
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from k_loto.application import achievement_catalog, achievement_release
from k_loto.application.achievement_release import (
    activate_due,
    cancel_schedule,
    pause_processing,
    queue_health,
    schedule_production,
)
from k_loto.application.achievements import process_one
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementDefinition,
    AchievementEvent,
    AchievementPlayer,
    AchievementRuntime,
)
from k_loto.infrastructure.database.models import Balance, LedgerTransaction
from test_achievements import pg as pg
from test_achievements import seed, tickets
from test_common_achievements import seed_catalog_games


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setattr(
        achievement_release,
        "get_settings",
        lambda: SimpleNamespace(app_env="production"),
    )


async def due(factory):
    # Move only the disposable fixture's scheduled clock; no real launch is backdated.
    async with factory() as session, session.begin():
        runtime = await session.get(AchievementRuntime, 1)
        runtime.scheduled_at = datetime.now(UTC) - timedelta(seconds=1)


async def schedule(factory):
    await seed_catalog_games(factory)
    at = datetime.now(UTC) + timedelta(hours=1)
    async with factory() as session, session.begin():
        await schedule_production(session, at)
    return at


async def ledger_count(factory):
    async with factory() as session:
        return await session.scalar(select(func.count()).select_from(LedgerTransaction))


async def test_requires_production_without_weakening_local_guards(pg, monkeypatch):
    async with pg() as session, session.begin():
        with pytest.raises(ValueError, match="APP_ENV=production"):
            await schedule_production(session, datetime.now(UTC) + timedelta(hours=1))
    monkeypatch.setattr(
        achievement_catalog,
        "get_settings",
        lambda: SimpleNamespace(app_env="production"),
    )
    async with pg() as session, session.begin():
        with pytest.raises(ValueError, match="local"):
            await achievement_catalog.launch_local(session)
        with pytest.raises(ValueError, match="local"):
            await achievement_catalog.import_catalog(session, [])


@pytest.mark.parametrize("at", [datetime(2026, 1, 1), datetime(2026, 1, 1, tzinfo=UTC)])
async def test_schedule_rejects_naive_or_past_clock(pg, production, at):
    async with pg() as session, session.begin():
        with pytest.raises(ValueError, match="timezone|future"):
            await schedule_production(session, at)


async def test_schedule_imports_93_without_awards_and_is_idempotent(pg, production):
    user, _, _ = await seed(pg)
    original_ledger_count = await ledger_count(pg)
    at = await schedule(pg)
    async with pg() as session, session.begin():
        runtime = await session.get(AchievementRuntime, 1)
        revision = runtime.catalog_revision
        assert not runtime.enabled and runtime.started_at is None
        assert (
            await session.scalar(
                select(func.count()).select_from(AchievementDefinition)
            )
            == 93
        )
        assert (
            await session.scalar(select(func.count()).select_from(AchievementAward))
            == 0
        )
        assert (
            await session.scalar(select(func.count()).select_from(LedgerTransaction))
            == original_ledger_count
        )
        assert await schedule_production(session, at) == at
        assert runtime.catalog_revision == revision
        assert await activate_due(session) is None
        assert (await session.get(Balance, user)).amount == 1_000_000


async def test_concurrent_activation_once_excludes_prelaunch_and_keeps_balance(
    pg, production
):
    user, lottery, draw = await seed(pg)
    original_ledger_count = await ledger_count(pg)
    await tickets(pg, user, lottery, draw, 1)
    await schedule(pg)
    await due(pg)

    async def start():
        async with pg() as session, session.begin():
            return await activate_due(session)

    results = await asyncio.gather(start(), start())
    assert sum(result is not None for result in results) == 1
    await tickets(pg, user, lottery, draw, 1, start=2)
    async with pg() as session, session.begin():
        runtime = await session.get(AchievementRuntime, 1)
        assert runtime.enabled and runtime.started_at
        assert await activate_due(session) is None
        player = await session.get(AchievementPlayer, user)
        assert player.metrics["baseline_balance"] == 1_000_000
        assert player.metrics.get("paid_tickets", 0) == 0
        purchases = list(
            await session.scalars(
                select(AchievementEvent).where(AchievementEvent.kind == "purchase")
            )
        )
        assert len(purchases) == 1 and purchases[0].payload["count"] == 1
        assert (await session.get(Balance, user)).amount == 1_000_000
        assert (
            await session.scalar(select(func.count()).select_from(LedgerTransaction))
            == original_ledger_count
        )
        with pytest.raises(ValueError, match="once-only"):
            await schedule_production(session, datetime.now(UTC) + timedelta(hours=2))
        with pytest.raises(ValueError, match="reset"):
            await cancel_schedule(session)


async def test_modified_catalog_refuses_due_activation(pg, production):
    await seed(pg)
    await schedule(pg)
    await due(pg)
    async with pg() as session, session.begin():
        runtime = await session.get(AchievementRuntime, 1)
        runtime.catalog_revision += 1
    async with pg() as session, session.begin():
        with pytest.raises(ValueError, match="catalog changed"):
            await activate_due(session)
        assert not (await session.get(AchievementRuntime, 1)).enabled


async def test_cancel_and_prelaunch_pause_block_activation(pg, production):
    await seed(pg)
    await schedule(pg)
    await due(pg)
    async with pg() as session, session.begin():
        await pause_processing(session, paused=True)
    async with pg() as session, session.begin():
        assert await activate_due(session) is None
        await cancel_schedule(session)
    async with pg() as session, session.begin():
        await pause_processing(session, paused=False)
        assert await activate_due(session) is None


async def test_processing_pause_preserves_capture_and_resumes_without_reset(
    pg, production
):
    user, lottery, draw = await seed(pg)
    await schedule(pg)
    await due(pg)
    async with pg() as session, session.begin():
        started = await activate_due(session)
        await pause_processing(session, paused=True)
    await tickets(pg, user, lottery, draw, 2)
    assert not await process_one(pg)
    async with pg() as session, session.begin():
        runtime = await session.get(AchievementRuntime, 1)
        assert runtime.enabled and runtime.started_at == started
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AchievementEvent)
                .where(AchievementEvent.kind == "purchase")
            )
            == 1
        )
        await pause_processing(session, paused=False)
    assert await process_one(pg)


async def test_queue_health_separates_ready_delayed_and_blocked(pg, production):
    user, _, _ = await seed(pg)
    await schedule(pg)
    await due(pg)
    now = datetime.now(UTC)
    async with pg() as session, session.begin():
        for key, attempts, delay in (
            ("ready", 0, -400),
            ("retry", 1, 300),
            ("blocked", 8, -500),
        ):
            session.add(
                AchievementEvent(
                    event_key=key,
                    user_id=user,
                    kind="evaluate",
                    payload={},
                    attempts=attempts,
                    available_at=now + timedelta(seconds=delay),
                )
            )
    async with pg() as session:
        health = await queue_health(session, now)
        assert health["ready"] == 1 and health["blocked"] == 1
        assert health["lag_seconds"] == 400


async def test_busy_source_defers_activation_without_waiting_on_gameplay(
    pg, production
):
    await seed(pg)
    await schedule(pg)
    await due(pg)
    async with pg() as source, source.begin():
        # A committed operation may still hold this table lock while completing
        # its ticket/ledger statements. Activation must yield immediately.
        await source.execute(text("LOCK TABLE balances IN ROW EXCLUSIVE MODE"))
        started = perf_counter()
        with pytest.raises(DBAPIError):
            async with pg() as session, session.begin():
                await activate_due(session)
        assert perf_counter() - started < 1.5
        assert await source.scalar(select(func.count()).select_from(Balance)) > 0
    async with pg() as session, session.begin():
        runtime = await session.get(AchievementRuntime, 1)
        assert not runtime.enabled and runtime.started_at is None
        assert await activate_due(session) is not None
