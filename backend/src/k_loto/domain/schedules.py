"""Official draw schedules expressed explicitly in Europe/Moscow."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from k_loto.domain.enums import LotteryKind

MOSCOW = ZoneInfo("Europe/Moscow")
WEEKLY_DRAW_TIME = time(20, 0)
WEEKLY_WEEKDAY = 6
WEEKLY_CUTOFF = timedelta(minutes=5)
DAILY_DRAW_TIMES = (time(2, 22), time(12, 0), time(18, 0))
DAILY_CUTOFF = timedelta(minutes=2)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Schedule calculations require a timezone-aware datetime.")
    return value


def _moscow_datetime(day: date, clock_time: time) -> datetime:
    return datetime.combine(day, clock_time, tzinfo=MOSCOW)


def next_weekly_draw(after: datetime) -> datetime:
    """Return the first Weekly Sunday 20:00 MSK strictly after `after`."""
    local = _aware(after).astimezone(MOSCOW)
    days_ahead = (WEEKLY_WEEKDAY - local.weekday()) % 7
    candidate = _moscow_datetime(
        local.date() + timedelta(days=days_ahead), WEEKLY_DRAW_TIME
    )
    if candidate <= local:
        candidate += timedelta(days=7)
    return candidate.astimezone(UTC)


def _parse_time(value: str) -> time:
    try:
        hour, minute = (int(part) for part in value.split(":"))
        return time(hour, minute)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid lottery draw time: {value!r}.") from error


def next_daily_draw(
    after: datetime, draw_times: tuple[time, ...] = DAILY_DRAW_TIMES
) -> datetime:
    """Return the first confirmed Daily slot strictly after `after`."""
    local = _aware(after).astimezone(MOSCOW)
    for day_offset in (0, 1):
        day = local.date() + timedelta(days=day_offset)
        for slot in sorted(draw_times):
            candidate = _moscow_datetime(day, slot)
            if candidate > local:
                return candidate.astimezone(UTC)
    raise AssertionError("A Daily slot must exist within the next day.")


def next_draw_at(
    kind: LotteryKind,
    after: datetime,
    schedule: dict[str, Any] | None = None,
) -> datetime:
    if kind == LotteryKind.WEEKLY:
        return next_weekly_draw(after)
    if kind == LotteryKind.DAILY:
        configured = schedule or {}
        raw_slots = configured.get("slots")
        if raw_slots is None and configured.get("draw_time"):
            raw_slots = [configured["draw_time"]]
        slots = (
            tuple(_parse_time(str(value)) for value in raw_slots)
            if raw_slots
            else DAILY_DRAW_TIMES
        )
        return next_daily_draw(after, slots)
    raise ValueError(f"Unsupported lottery kind: {kind}")


def sales_close_at(
    kind: LotteryKind,
    scheduled_at: datetime,
    cutoff_minutes: int | None = None,
) -> datetime:
    """Return the official sales close time for a prepared draw."""
    _aware(scheduled_at)
    if cutoff_minutes is not None:
        if cutoff_minutes < 0:
            raise ValueError("Sales cutoff cannot be negative.")
        return scheduled_at - timedelta(minutes=cutoff_minutes)
    if kind == LotteryKind.WEEKLY:
        return scheduled_at - WEEKLY_CUTOFF
    if kind == LotteryKind.DAILY:
        return scheduled_at - DAILY_CUTOFF
    raise ValueError(f"Unsupported lottery kind: {kind}")
