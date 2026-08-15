"""Milestone 3 schedule preparation and recovery tests."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.application.scheduler import DrawRecoveryService, DrawScheduleService
from k_loto.application.weekly import SettlementResult, WeeklySettlementService
from k_loto.domain.enums import DrawStatus, LotteryKind
from k_loto.domain.schedules import (
    next_daily_draw,
    next_weekly_draw,
    sales_close_at,
)
from k_loto.infrastructure.database.models import Draw, Lottery

MOSCOW = ZoneInfo("Europe/Moscow")


class TransactionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeSession:
    def __init__(self, scalar_values: list[Any]) -> None:
        self.scalar_values = iter(scalar_values)
        self.added: list[Any] = []

    def begin(self) -> TransactionContext:
        return TransactionContext()

    async def scalar(self, _statement: object) -> Any:
        return next(self.scalar_values)

    def add(self, item: Any) -> None:
        self.added.append(item)


class DummySessionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: object) -> None:
        return None


class DummySessionFactory:
    def __call__(self) -> DummySessionContext:
        return DummySessionContext()


def local(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=MOSCOW)


def test_weekly_schedule_is_sunday_20_moscow_with_1955_cutoff() -> None:
    scheduled = next_weekly_draw(local(2026, 8, 16, 19, 54))

    assert scheduled.astimezone(MOSCOW) == local(2026, 8, 16, 20, 0)
    assert sales_close_at(LotteryKind.WEEKLY, scheduled).astimezone(MOSCOW) == local(
        2026, 8, 16, 19, 55
    )


def test_weekly_schedule_is_strictly_next_after_exact_draw_time() -> None:
    scheduled = next_weekly_draw(local(2026, 8, 16, 20, 0))

    assert scheduled.astimezone(MOSCOW) == local(2026, 8, 23, 20, 0)


@pytest.mark.parametrize(
    ("after", "expected"),
    [
        (local(2026, 8, 14, 1, 0), local(2026, 8, 14, 2, 22)),
        (local(2026, 8, 14, 2, 22), local(2026, 8, 14, 18, 0)),
        (local(2026, 8, 14, 18, 0), local(2026, 8, 15, 2, 22)),
    ],
)
def test_daily_confirmed_slots(after: datetime, expected: datetime) -> None:
    assert next_daily_draw(after).astimezone(MOSCOW) == expected


def test_daily_sales_close_two_minutes_before_both_slots() -> None:
    for scheduled in (local(2026, 8, 14, 2, 22), local(2026, 8, 14, 18, 0)):
        assert sales_close_at(LotteryKind.DAILY, scheduled.astimezone(UTC)).astimezone(
            MOSCOW
        ) == scheduled - timedelta(minutes=2)


def test_schedule_rejects_naive_server_time() -> None:
    with pytest.raises(ValueError):
        next_weekly_draw(datetime(2026, 8, 14, 12, 0))


def weekly_lottery() -> Lottery:
    return Lottery(
        id=UUID(int=1),
        code="weekly",
        name="Weekly 5/20",
        kind=LotteryKind.WEEKLY,
        numbers_to_pick=5,
        max_number=20,
        ticket_price=100,
        timezone="Europe/Moscow",
        schedule={},
        sales_cutoff_minutes=5,
        is_active=True,
        next_draw_number=7,
        next_ticket_number=1,
    )


async def test_next_draw_creation_allocates_number_once() -> None:
    lottery = weekly_lottery()
    fake = FakeSession([lottery, None, None])
    service = DrawScheduleService(cast(AsyncSession, fake))

    draw, created = await service.ensure_next_draw(
        lottery.id, reference=local(2026, 8, 14, 12, 0)
    )

    assert created
    assert draw.public_number == 7
    assert draw.scheduled_at.astimezone(MOSCOW) == local(2026, 8, 16, 20, 0)
    assert draw.sales_close_at.astimezone(MOSCOW) == local(2026, 8, 16, 19, 55)
    assert lottery.next_draw_number == 8
    assert fake.added == [draw]


async def test_existing_pending_draw_prevents_duplicate_creation() -> None:
    lottery = weekly_lottery()
    pending = Draw(
        id=UUID(int=2),
        lottery_id=lottery.id,
        public_number=7,
        status=DrawStatus.SCHEDULED,
        scheduled_at=local(2026, 8, 16, 20, 0).astimezone(UTC),
        sales_close_at=local(2026, 8, 16, 19, 55).astimezone(UTC),
        correlation_id=UUID(int=3),
        ticket_count=0,
        total_sales=0,
        total_payout=0,
        reserve_used=0,
    )
    fake = FakeSession([lottery, pending])

    draw, created = await DrawScheduleService(
        cast(AsyncSession, fake)
    ).ensure_next_draw(lottery.id, reference=datetime.now(UTC))

    assert draw is pending
    assert not created
    assert lottery.next_draw_number == 7
    assert fake.added == []


async def test_cutoff_prepares_next_weekly_draw_before_current_settlement() -> None:
    lottery = weekly_lottery()
    closing_draw = Draw(
        id=UUID(int=2),
        lottery_id=lottery.id,
        public_number=6,
        status=DrawStatus.SCHEDULED,
        scheduled_at=local(2026, 8, 16, 20, 0).astimezone(UTC),
        sales_close_at=local(2026, 8, 16, 19, 55).astimezone(UTC),
        correlation_id=UUID(int=3),
        ticket_count=0,
        total_sales=0,
        total_payout=0,
        reserve_used=0,
    )
    fake = FakeSession([lottery, None, closing_draw])

    draw, created = await DrawScheduleService(
        cast(AsyncSession, fake)
    ).ensure_next_draw(lottery.id, reference=local(2026, 8, 16, 19, 55).astimezone(UTC))

    assert created
    assert draw.public_number == 7
    assert draw.scheduled_at.astimezone(MOSCOW) == local(2026, 8, 23, 20, 0)
    assert lottery.next_draw_number == 8


async def test_recovery_processes_multiple_missed_draws_chronologically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lottery_id = UUID(int=10)
    draw_ids = [UUID(int=11), UUID(int=12)]
    service = DrawRecoveryService(
        cast(async_sessionmaker[AsyncSession], DummySessionFactory())
    )
    monkeypatch.setattr(
        service, "_active_lottery_ids", AsyncMock(return_value=[lottery_id])
    )
    monkeypatch.setattr(
        service,
        "_next_due_draw",
        AsyncMock(side_effect=[draw_ids[0], draw_ids[1], None]),
    )
    monkeypatch.setattr(
        service, "_lottery_id_for_draw", AsyncMock(return_value=lottery_id)
    )
    monkeypatch.setattr(
        service, "_lottery_kind_for_draw", AsyncMock(return_value=LotteryKind.WEEKLY)
    )
    settled: list[UUID] = []
    prepared = iter([UUID(int=20), UUID(int=21), UUID(int=22)])

    async def fake_ensure(
        _self: DrawScheduleService, _lottery_id: UUID, *, reference: datetime
    ) -> tuple[Any, bool]:
        assert reference.tzinfo is not None
        return SimpleNamespace(id=next(prepared)), True

    async def fake_settle(
        _self: WeeklySettlementService, draw_id: UUID, *, now: datetime | None = None
    ) -> SettlementResult:
        settled.append(draw_id)
        return SettlementResult(draw_id, (1, 2, 3, 4, 5), 0)

    monkeypatch.setattr(DrawScheduleService, "ensure_next_draw", fake_ensure)
    monkeypatch.setattr(WeeklySettlementService, "settle", fake_settle)

    report = await service.reconcile(now=local(2026, 8, 30, 21, 0).astimezone(UTC))

    assert settled == draw_ids
    assert report.settled_draw_ids == tuple(draw_ids)
    assert report.prepared_draw_ids == (UUID(int=20), UUID(int=21), UUID(int=22))
