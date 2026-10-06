"""Platform event boundaries, replay safety and existing editorial compatibility."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.publication_events import (
    EVENTS,
    EventDraftInput,
    MilestoneRule,
    PublicationEventService,
    day_bounds,
    due_slot,
    event_config,
    event_content,
)
from k_loto.application.publications import PublicationConflict, PublicationService
from k_loto.infrastructure.database.models import Publication, PublicationEventState
from k_loto.main import create_app

NOW = datetime(2026, 10, 6, 16, tzinfo=UTC)
AUTHOR = UUID(int=1)


def test_registry_exact_scope_and_modes_no_unrequested_categories() -> None:
    assert set(EVENTS) == {
        *(f"B1.{n}" for n in range(1, 5)),
        "B2.1",
        *(f"B3.{n}" for n in range(1, 6)),
        *(f"B4.{n}" for n in range(1, 9)),
    }
    assert {e.code for e in EVENTS.values() if e.mode == "automatic"} == {
        "B1.1",
        "B1.2",
        "B1.3",
        "B1.4",
        "B2.1",
        "B3.5",
    }
    assert all(e.scope == "platform" for e in EVENTS.values())


def test_milestone_crossings_inclusive_and_programmatic_continuation() -> None:
    config = event_config()
    assert config.milestones["B1.1"].reached(999) == []
    assert config.milestones["B1.1"].reached(1000) == [1000]
    for code in ("B1.2", "B1.4"):
        rule = config.milestones[code]
        assert rule.reached(14_999_999)[-1] == 10_000_000
        assert rule.reached(30_000_000)[-4:] == [
            15_000_000,
            20_000_000,
            25_000_000,
            30_000_000,
        ]
    assert config.milestones["B1.3"].reached(2_000_000)[-2:] == [1_500_000, 2_000_000]
    changed = MilestoneRule(
        metric="purchased_tickets", thresholds=[5, 9], repeat_after=9, repeat_step=3
    )
    assert changed.reached(16) == [5, 9, 12, 15]


@pytest.mark.parametrize(
    "grid",
    [
        {"thresholds": [0]},
        {"thresholds": [9, 5]},
        {"thresholds": [5, 5]},
        {"thresholds": [5], "repeat_after": 5},
        {"thresholds": [5], "repeat_after": 4, "repeat_step": 2},
    ],
)
def test_invalid_grid_fails_before_scan(grid: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        MilestoneRule(metric="x", **grid)


def test_moscow_calendar_slots_recovery_and_manual_queue_bypass() -> None:
    config = event_config()
    start, end = day_bounds(date(2026, 10, 6))
    assert start == datetime(2026, 10, 5, 21, tzinfo=UTC)
    assert end == datetime(2026, 10, 6, 21, tzinfo=UTC)
    assert (
        due_slot(datetime(2026, 10, 6, 9, 21, tzinfo=UTC), config) == "2026-10-05T22:22"
    )
    assert (
        due_slot(datetime(2026, 10, 6, 9, 22, tzinfo=UTC), config) == "2026-10-06T12:22"
    )
    assert due_slot(NOW, config) == "2026-10-06T18:35"
    assert config.delivery.earliest(NOW, NOW - timedelta(minutes=5)) == NOW + timedelta(
        minutes=25
    )
    assert config.delivery.earliest(NOW, NOW, manual=True) == NOW
    assert config.delivery.daily_limit is None and not config.delivery.enabled
    with pytest.raises(ValueError):
        due_slot(NOW.replace(tzinfo=None), config)


def test_data_contract_has_separate_block_batch_and_no_visual_content() -> None:
    data = event_content(
        "B1.4",
        {"metric": "winning_tickets", "threshold": 100_000},
        NOW,
        batch="B:scan:one",
    )
    assert data["event"]["block"] == "B" and data["event"]["category"] == "B1"
    assert data["delivery"]["batch_key"] == "B:scan:one"
    assert data["delivery"]["state"] == "awaiting_content_and_visual"
    assert "template" not in data and "fields" not in data


def test_manual_types_and_explicit_statistical_periods() -> None:
    for code in ("B1.1", "B2.1", "B3.5", "B9.1"):
        with pytest.raises(ValidationError):
            EventDraftInput(event_type=code)
    for code in ("B3.3", "B3.4"):
        with pytest.raises(ValidationError):
            EventDraftInput(event_type=code)
    with pytest.raises(ValidationError):
        EventDraftInput(
            event_type="B3.3", period_start=NOW - timedelta(days=1), period_end=NOW
        )
    assert (
        EventDraftInput(
            event_type="B3.3", period_start=NOW - timedelta(days=7), period_end=NOW
        ).event_type
        == "B3.3"
    )
    assert all(EventDraftInput(event_type=f"B4.{n}").event_type for n in range(1, 9))


class Transaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *_args: Any) -> None:
        return None


class MemorySession:
    def __init__(self) -> None:
        self.states: dict[str, PublicationEventState] = {}
        self.events: dict[str, Publication] = {}
        self.row: Publication | None = None
        self.added: list[Any] = []

    def begin(self) -> Transaction:
        return Transaction()

    async def execute(self, _query: Any) -> Any:
        return None

    async def scalar(self, query: Any) -> Any:
        compiled = query.compile()
        key = next(
            (
                v
                for v in compiled.params.values()
                if isinstance(v, str)
                and (
                    ":milestone:" in v
                    or ":draft:" in v
                    or ":day:" in v
                    or ":record:" in v
                )
            ),
            None,
        )
        return self.events.get(key) if key else AUTHOR

    async def get(self, model: Any, key: Any, **_kwargs: Any) -> Any:
        if model is PublicationEventState:
            return self.states.get(key)
        return self.row or next((r for r in self.events.values() if r.id == key), None)

    async def flush(self) -> None:
        pass

    def add(self, row: Any) -> None:
        self.added.append(row)
        if isinstance(row, PublicationEventState):
            self.states[row.key] = row
        elif isinstance(row, Publication):
            assert row.event_key is not None
            self.events[row.event_key] = row


class FixedMetricsService(PublicationEventService):
    async def metrics(self) -> dict[str, int]:
        return {
            "registered_players": 5000,
            "purchased_tickets": 500_000,
            "completed_draws": 25_000,
            "winning_tickets": 100_000,
        }

    async def _record(self, _now: datetime, _author: UUID, _batch: str) -> None:
        pass

    async def _daily_jackpots(self, _now: datetime, _author: UUID) -> None:
        pass


async def test_multiple_thresholds_replays_archived_and_published_never_duplicate() -> (
    None
):
    session = MemorySession()
    service = FixedMetricsService(cast(AsyncSession, session))
    result = await service.scan(now=NOW, author=AUTHOR)
    assert result["counters"]["completed_draws"] == 25_000
    assert len(session.events) == 9
    ids = {e.id for e in session.events.values()}
    for event in session.events.values():
        assert event.event_mode == "automatic" and event.status == "draft"
        event.status = "archived"
    assert (await service.scan(now=NOW, author=AUTHOR))["skipped"]
    await service.scan(now=NOW + timedelta(days=1), author=AUTHOR)
    await service.scan(now=NOW, author=AUTHOR, force=True)
    assert {e.id for e in session.events.values()} == ids
    assert (
        len({e.content["delivery"]["batch_key"] for e in session.events.values()}) == 1
    )


async def test_b4_uses_existing_draft_storage_and_retry_guard() -> None:
    session = MemorySession()
    service = PublicationEventService(cast(AsyncSession, session))
    request = EventDraftInput(event_type="B4.1", fields={"title": "Новая функция"})
    row = await service.create_draft(
        request, publication_id=UUID(int=3), author=AUTHOR, now=NOW
    )
    assert (
        isinstance(row, Publication)
        and row.status == "draft"
        and row.event_mode == "draft"
    )
    assert (
        await service.create_draft(
            request, publication_id=UUID(int=3), author=AUTHOR, now=NOW
        )
        is row
    )
    with pytest.raises(PublicationConflict):
        await service.create_draft(
            request, publication_id=UUID(int=3), author=UUID(int=4), now=NOW
        )
    session.row = row
    with pytest.raises(PublicationConflict):
        await PublicationService(cast(AsyncSession, session)).change(
            row.id, author=AUTHOR, revision=1, action="publish"
        )
    with pytest.raises(ValueError):
        await PublicationService(cast(AsyncSession, session)).list(
            player=True, events=True
        )


async def test_daily_refresh_keeps_one_draft_and_preserves_published_history() -> None:
    session = MemorySession()
    service = PublicationEventService(cast(AsyncSession, session))
    key = "B3.5:day:2026-10-06"
    row = await service._store(
        key, "B3.5", {"count": 4}, NOW, AUTHOR, "B:day:2026-10-06"
    )
    await service._store(
        key, "B3.5", {"count": 5}, NOW, AUTHOR, "B:day:2026-10-06", refresh=True
    )
    assert len(session.events) == 1 and row.content["event"]["payload"]["count"] == 5
    row.status = "published"
    await service._store(
        key, "B3.5", {"count": 6}, NOW, AUTHOR, "B:day:2026-10-06", refresh=True
    )
    assert row.content["event"]["payload"]["count"] == 5


@pytest.mark.parametrize("path", ["event-types", "events"])
def test_event_reads_require_admin_auth(path: str) -> None:
    assert (
        TestClient(create_app()).get(f"/api/v1/admin/publications/{path}").status_code
        == 401
    )


class RecordSession(MemorySession):
    current = 200000000

    async def scalar(self, query: Any) -> Any:
        sql = str(query)
        if "max(" in sql:
            return 100000000 if "ledger_transactions" in sql else 0
        return await super().scalar(query)

    async def execute(self, _query: Any) -> Any:
        return SimpleNamespace(
            first=lambda: SimpleNamespace(
                balance=self.current,
                code="weekly",
                id=UUID(int=8),
                jackpot_account_id=UUID(int=9),
            )
        )


async def test_record_strict_increase_keeps_previous_value_and_stable_key() -> None:
    session = RecordSession()
    service = PublicationEventService(cast(AsyncSession, session))
    await service._record(NOW, AUTHOR, "B:scan:one")
    row = session.events["B2.1:record:200000000"]
    assert row.content["event"]["payload"]["previous_record"] == 100000000
    await service._record(NOW, AUTHOR, "B:scan:one")
    session.current = 150000000
    await service._record(NOW, AUTHOR, "B:scan:one")
    assert len(session.events) == 1
    session.current = 225000000
    await service._record(NOW, AUTHOR, "B:scan:small")
    assert len(session.events) == 1
    session.current = 300000000
    await service._record(NOW, AUTHOR, "B:scan:two")
    assert (
        session.events["B2.1:record:300000000"].content["event"]["payload"][
            "previous_record"
        ]
        == 225000000
    )


class WinsSession(MemorySession):
    wins: list[Any] = []

    async def execute(self, _query: Any) -> Any:
        return SimpleNamespace(all=lambda: self.wins)


async def test_fourth_jackpot_and_moscow_day_aggregation() -> None:
    session = WinsSession()
    service = PublicationEventService(cast(AsyncSession, session))
    start, end = day_bounds(date(2026, 10, 6))
    session.wins = [
        (
            SimpleNamespace(
                id=UUID(int=i),
                draw_id=UUID(int=i + 20),
                occurred_at=start + timedelta(hours=i),
                jackpot_amount=100,
            ),
            "weekly",
        )
        for i in range(1, 4)
    ]
    await service._daily_jackpots(NOW, AUTHOR)
    assert not session.events
    session.wins.append(
        (
            SimpleNamespace(
                id=UUID(int=4),
                draw_id=UUID(int=24),
                occurred_at=NOW,
                jackpot_amount=100,
            ),
            "shadow",
        )
    )
    await service._daily_jackpots(NOW, AUTHOR)
    row = session.events["B3.5:day:2026-10-06"]
    assert len(row.content["event"]["payload"]["jackpots"]) == 4
    assert row.content["delivery"]["ready_after"] == end.isoformat()
    session.wins.append(
        (
            SimpleNamespace(
                id=UUID(int=5),
                draw_id=UUID(int=25),
                occurred_at=start - timedelta(seconds=1),
                jackpot_amount=100,
            ),
            "pulse",
        )
    )
    await service._daily_jackpots(NOW, AUTHOR)
    assert len(session.events) == 1 and row.content["event"]["payload"]["count"] == 4
