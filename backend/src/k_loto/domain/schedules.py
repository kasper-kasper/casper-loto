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


def next_interval_draw(
    after: datetime, *, interval_minutes: int, anchor_time: time = time(0, 0)
) -> datetime:
    """Return the next Moscow wall-clock interval, useful for fast lotteries."""
    if not 1 <= interval_minutes <= 1440:
        raise ValueError("Lottery interval must be between 1 and 1440 minutes.")
    local = _aware(after).astimezone(MOSCOW)
    anchor = _moscow_datetime(local.date(), anchor_time)
    if anchor > local:
        return anchor.astimezone(UTC)
    elapsed_minutes = int((local - anchor).total_seconds() // 60)
    steps = elapsed_minutes // interval_minutes + 1
    return (anchor + timedelta(minutes=steps * interval_minutes)).astimezone(UTC)


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
    configured = schedule or {}
    schedule_type = configured.get("type")
    if schedule_type == "interval":
        return next_interval_draw(
            after,
            interval_minutes=int(configured["interval_minutes"]),
            anchor_time=_parse_time(str(configured.get("anchor_time", "00:00"))),
        )
    if kind == LotteryKind.WEEKLY:
        return next_weekly_draw(after)
    if kind == LotteryKind.DAILY:
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


def future_draw_target(kind: LotteryKind, schedule: dict[str, Any] | None) -> int:
    """How many future draws should be prepared for a schedule strategy."""
    configured = schedule or {}
    explicit = configured.get("future_draw_count")
    if explicit is not None:
        value = int(explicit)
        if not 1 <= value <= 20:
            raise ValueError("future_draw_count must be between 1 and 20.")
        return value
    if configured.get("type") == "interval":
        return 2
    if kind == LotteryKind.DAILY:
        return max(len(configured.get("slots", [])), 1)
    return 1


def sales_close_at(
    kind: LotteryKind,
    scheduled_at: datetime,
    cutoff_minutes: int | None = None,
    schedule: dict[str, Any] | None = None,
) -> datetime:
    """Return the official sales close time for a prepared draw."""
    _aware(scheduled_at)
    cutoff_seconds = (schedule or {}).get("sales_cutoff_seconds")
    if cutoff_seconds is not None:
        seconds = int(cutoff_seconds)
        if not 0 <= seconds <= 86_400:
            raise ValueError("Sales cutoff seconds are outside the valid range.")
        return scheduled_at - timedelta(seconds=seconds)
    if cutoff_minutes is not None:
        if cutoff_minutes < 0:
            raise ValueError("Sales cutoff cannot be negative.")
        return scheduled_at - timedelta(minutes=cutoff_minutes)
    if kind == LotteryKind.WEEKLY:
        return scheduled_at - WEEKLY_CUTOFF
    if kind == LotteryKind.DAILY:
        return scheduled_at - DAILY_CUTOFF
    raise ValueError(f"Unsupported lottery kind: {kind}")
