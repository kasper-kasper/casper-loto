"""Retiring editorial work must not perform SQL, send posts or disable draws."""

from collections import Counter
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application import (
    distribution,
    publication_automation,
    publication_monitoring,
)
from k_loto.core.config import Settings
from k_loto.infrastructure import scheduler


@pytest.fixture
def retired(monkeypatch):
    settings = SimpleNamespace(
        editorial_enabled=False, achievements_worker_enabled=False
    )
    for module in (scheduler, distribution, publication_automation):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
    monkeypatch.setattr("k_loto.core.config.get_settings", lambda: settings)
    return settings


async def test_retired_scheduler_does_not_open_database(retired, monkeypatch):
    factory = Mock(side_effect=AssertionError("Editorial SQL must not run"))
    monkeypatch.setattr(scheduler, "session_factory", factory)
    runtime = scheduler.SchedulerRuntime.__new__(scheduler.SchedulerRuntime)
    await runtime._run_publication_events()
    await runtime._run_publication_delivery()
    factory.assert_not_called()


async def test_retired_scheduler_installs_no_editorial_timers(retired):
    runtime = scheduler.SchedulerRuntime.__new__(scheduler.SchedulerRuntime)
    runtime._scheduler = Mock()
    runtime._interval_seconds = 30
    runtime._run = AsyncMock()
    runtime._run_owner_economy = AsyncMock()
    runtime._run_publication_events = AsyncMock()
    await runtime.start()
    runtime._run_publication_events.assert_not_called()
    jobs = [call.kwargs["id"] for call in runtime._scheduler.add_job.call_args_list]
    assert jobs == ["owner-daily-economy", "draw-reconciliation"]
    runtime._run.assert_awaited_once()
    runtime._scheduler.start.assert_called_once()


async def test_retired_queues_and_monitoring_do_not_touch_database(retired):
    factory = Mock(side_effect=AssertionError("Editorial SQL must not run"))
    session = AsyncMock(spec=AsyncSession)
    now = datetime.now(UTC)
    await distribution.recover_results(factory, now=now)
    await distribution.drain_distribution(factory)
    await publication_automation.drain(factory)
    assert (
        await publication_monitoring.delayed_publications(
            session, now=now, grace=timedelta(minutes=10)
        )
        == 0
    )
    distribution.queue_result(session, Mock(), Mock(), Counter(), 0, now)
    factory.assert_not_called()
    session.add.assert_not_called()
    session.scalar.assert_not_called()


def test_retired_editorial_api_cannot_recreate_history(retired, monkeypatch):
    from k_loto.api.routes import publications

    monkeypatch.setattr(publications, "get_settings", lambda: retired)
    with pytest.raises(HTTPException) as error:
        publications.require_editorial_enabled()
    assert error.value.status_code == 410


async def test_distribution_assignment_survives_channel_retirement(retired):
    from test_weekly_application import FakeSession, build_purchase_accounts

    now = datetime(2099, 10, 4, 9, tzinfo=UTC)
    _, lottery, draw, *_ = build_purchase_accounts(now)

    class Session(FakeSession):
        async def get(self, *_args, **_kwargs):
            return lottery

    session = Session(scalar_values=[draw, 1001, None])
    result = await distribution.DistributionDrawService(session).assign(
        draw.id, UUID(int=99), now=now
    )
    assert result["is_distribution"]
    assert [type(row).__name__ for row in session.added] == ["AdminAuditLog"]


def test_production_compose_explicitly_disables_editorial():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    compose = (root / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert compose.count('EDITORIAL_ENABLED: "false"') == 2
    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        editorial_enabled=False,
    )
    assert not settings.editorial_enabled
