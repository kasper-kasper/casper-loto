"""Official draw schedules expressed explicitly in Europe/Moscow."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from k_loto.domain.enums import LotteryKind

MOSCOW = ZoneInfo("Europe/Moscow")
WEEKLY_DRAW_TIME = time(20, 0)
WEEKLY_WEEKDAY = 6
WEEKLY_CUTOFF = timedelta(minutes=5)
DAILY_DRAW_TIMES = (time(2, 22), time(18, 0))


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


def next_daily_draw(after: datetime) -> datetime:
    """Return the first confirmed Daily slot strictly after `after`."""
    local = _aware(after).astimezone(MOSCOW)
    for day_offset in (0, 1):
        day = local.date() + timedelta(days=day_offset)
        for slot in DAILY_DRAW_TIMES:
            candidate = _moscow_datetime(day, slot)
            if candidate > local:
                return candidate.astimezone(UTC)
    raise AssertionError("A Daily slot must exist within the next day.")


def next_draw_at(kind: LotteryKind, after: datetime) -> datetime:
    if kind == LotteryKind.WEEKLY:
        return next_weekly_draw(after)
    if kind == LotteryKind.DAILY:
        return next_daily_draw(after)
    raise ValueError(f"Unsupported lottery kind: {kind}")


def sales_close_at(kind: LotteryKind, scheduled_at: datetime) -> datetime:
    """Return the official sales close time for a prepared draw."""
    _aware(scheduled_at)
    if kind == LotteryKind.WEEKLY:
        return scheduled_at - WEEKLY_CUTOFF
    # Daily sales are not implemented; cutoff remains an open business decision.
    return scheduled_at
