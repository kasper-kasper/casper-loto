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
from k_loto.application.weekly import LotterySettlementService, SettlementResult
from k_loto.domain.enums import DrawStatus, LotteryKind
from k_loto.domain.schedules import (
    next_daily_draw,
    next_draw_at,
    next_weekly_draw,
    sales_close_at,
)
from k_loto.infrastructure.database.models import Draw, JackpotAccount, Lottery

MOSCOW = ZoneInfo("Europe/Moscow")


class TransactionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeSession:
    def __init__(
        self, scalar_values: list[Any], scalar_rows: list[list[Any]] | None = None
    ) -> None:
        self.scalar_values = iter(scalar_values)
        self.scalar_rows = iter(scalar_rows or [])
        self.added: list[Any] = []

    def begin(self) -> TransactionContext:
        return TransactionContext()

    async def scalar(self, _statement: object) -> Any:
        return next(self.scalar_values)

    async def scalars(self, _statement: object) -> Any:
        return SimpleNamespace(all=lambda: next(self.scalar_rows))

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
        (local(2026, 8, 14, 2, 22), local(2026, 8, 14, 12, 0)),
        (local(2026, 8, 14, 12, 0), local(2026, 8, 14, 18, 0)),
        (local(2026, 8, 14, 18, 0), local(2026, 8, 15, 2, 22)),
    ],
)
def test_daily_confirmed_slots(after: datetime, expected: datetime) -> None:
    assert next_daily_draw(after).astimezone(MOSCOW) == expected


def test_daily_sales_close_two_minutes_before_all_slots() -> None:
    for scheduled in (
        local(2026, 8, 14, 2, 22),
        local(2026, 8, 14, 12, 0),
        local(2026, 8, 14, 18, 0),
    ):
        assert sales_close_at(LotteryKind.DAILY, scheduled.astimezone(UTC)).astimezone(
            MOSCOW
        ) == scheduled - timedelta(minutes=2)


def test_configured_fast_sales_close_uses_seconds() -> None:
    scheduled = local(2026, 9, 4, 12, 0).astimezone(UTC)

    assert sales_close_at(
        LotteryKind.DAILY,
        scheduled,
        1,
        {"sales_cutoff_seconds": 8},
    ) == scheduled - timedelta(seconds=8)


@pytest.mark.parametrize(
    ("draw_time", "expected"),
    [
        ("02:22", local(2026, 8, 15, 2, 22)),
        ("12:00", local(2026, 8, 15, 12, 0)),
        ("18:00", local(2026, 8, 14, 18, 0)),
    ],
)
def test_named_daily_lotteries_use_independent_moscow_slots(
    draw_time: str, expected: datetime
) -> None:
    scheduled = next_draw_at(
        LotteryKind.DAILY,
        local(2026, 8, 14, 13, 0),
        {"draw_time": draw_time},
    )

    assert scheduled.astimezone(MOSCOW) == expected


@pytest.mark.parametrize(
    ("slots", "after", "expected"),
    [
        (["09:00", "18:00"], local(2026, 9, 2, 8, 0), local(2026, 9, 2, 9, 0)),
        (["02:22", "13:45"], local(2026, 9, 2, 3, 0), local(2026, 9, 2, 13, 45)),
        (["12:00", "20:30"], local(2026, 9, 2, 13, 0), local(2026, 9, 2, 20, 30)),
    ],
)
def test_new_daily_slots(slots: list[str], after: datetime, expected: datetime) -> None:
    scheduled = next_draw_at(LotteryKind.DAILY, after, {"slots": slots})

    assert scheduled.astimezone(MOSCOW) == expected


def test_bingo_uses_morning_and_evening_moscow_slots() -> None:
    schedule = {"slots": ["10:30", "22:00"], "future_draw_count": 2}

    assert next_draw_at(
        LotteryKind.DAILY, local(2026, 9, 2, 9, 0), schedule
    ).astimezone(MOSCOW) == local(2026, 9, 2, 10, 30)
    assert next_draw_at(
        LotteryKind.DAILY, local(2026, 9, 2, 10, 30), schedule
    ).astimezone(MOSCOW) == local(2026, 9, 2, 22, 0)


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


def daily_lottery() -> Lottery:
    return Lottery(
        id=UUID(int=101),
        code="daily",
        name="Ежедневная лотерея",
        kind=LotteryKind.DAILY,
        numbers_to_pick=4,
        max_number=15,
        ticket_price=24_000,
        timezone="Europe/Moscow",
        schedule={"slots": ["02:22", "12:00", "18:00"]},
        sales_cutoff_minutes=2,
        is_active=True,
        next_draw_number=30,
        next_ticket_number=1,
    )


def jackpot(lottery: Lottery) -> JackpotAccount:
    return JackpotAccount(
        id=UUID(int=900),
        lottery_id=lottery.id,
        balance=1_000_000,
        base_amount=1_000_000,
        version=1,
    )


async def test_daily_scheduler_keeps_all_three_named_slots_ready() -> None:
    lottery = daily_lottery()
    fake = FakeSession([lottery, jackpot(lottery), None], scalar_rows=[[]])

    first, created = await DrawScheduleService(
        cast(AsyncSession, fake)
    ).ensure_next_draw(lottery.id, reference=local(2026, 8, 14, 1, 0).astimezone(UTC))

    assert created
    assert first is fake.added[0]
    assert [draw.public_number for draw in fake.added] == [30, 31, 32]
    assert [draw.scheduled_at.astimezone(MOSCOW) for draw in fake.added] == [
        local(2026, 8, 14, 2, 22),
        local(2026, 8, 14, 12, 0),
        local(2026, 8, 14, 18, 0),
    ]
    assert lottery.next_draw_number == 33


async def test_next_draw_creation_allocates_number_once() -> None:
    lottery = weekly_lottery()
    fake = FakeSession([lottery, None, jackpot(lottery), None])
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
    fake = FakeSession([lottery, None, jackpot(lottery), closing_draw])

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
        "k_loto.application.daily_transition.DailyTransitionService.finalize_if_ready",
        AsyncMock(return_value=False),
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
    monkeypatch.setattr(service, "_lottery_is_active", AsyncMock(return_value=True))
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
        _self: LotterySettlementService, draw_id: UUID, *, now: datetime | None = None
    ) -> SettlementResult:
        settled.append(draw_id)
        return SettlementResult(draw_id, (1, 2, 3, 4, 5), 0)

    monkeypatch.setattr(DrawScheduleService, "ensure_next_draw", fake_ensure)
    monkeypatch.setattr(LotterySettlementService, "settle", fake_settle)

    report = await service.reconcile(now=local(2026, 8, 30, 21, 0).astimezone(UTC))

    assert settled == draw_ids
    assert report.settled_draw_ids == tuple(draw_ids)
    assert report.prepared_draw_ids == (UUID(int=20), UUID(int=21), UUID(int=22))
