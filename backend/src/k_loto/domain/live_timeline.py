"""Server-authoritative presentation timeline for a digital draw broadcast."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from k_loto.domain.enums import DrawStatus

REVEAL_LEAD = timedelta(seconds=1)
REVEAL_INTERVAL = timedelta(seconds=2)
FAST_REVEAL_LEAD = timedelta(milliseconds=500)
FAST_REVEAL_INTERVAL = timedelta(seconds=1)
KHAN_REVEAL_LEAD = timedelta(seconds=4)
KHAN_REVEAL_INTERVAL = timedelta(milliseconds=4700)
CUTOFF_SOON = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class DrawTimeline:
    starts_at: datetime
    reveal_at: tuple[datetime, ...]
    ends_at: datetime


def draw_timeline(scheduled_at: datetime, number_count: int) -> DrawTimeline:
    reveal_at = tuple(
        scheduled_at + REVEAL_LEAD + REVEAL_INTERVAL * index
        for index in range(number_count)
    )
    ends_at = (
        reveal_at[-1] + REVEAL_INTERVAL if reveal_at else scheduled_at + REVEAL_LEAD
    )
    return DrawTimeline(scheduled_at, reveal_at, ends_at)


def presentation_timeline(
    scheduled_at: datetime,
    executed_at: datetime | None,
    number_count: int,
) -> DrawTimeline:
    """Start visual reveal only when the immutable result is actually available."""

    starts_at = max(scheduled_at, executed_at) if executed_at else scheduled_at
    return draw_timeline(starts_at, number_count)


def khan_presentation_timeline(
    scheduled_at: datetime,
    executed_at: datetime | None,
    number_count: int,
) -> DrawTimeline:
    """Give the 6-of-36 drum enough time to mix and present every ball."""

    starts_at = max(scheduled_at, executed_at) if executed_at else scheduled_at
    reveal_at = tuple(
        starts_at + KHAN_REVEAL_LEAD + KHAN_REVEAL_INTERVAL * index
        for index in range(number_count)
    )
    ends_at = (
        reveal_at[-1] + KHAN_REVEAL_INTERVAL
        if reveal_at
        else starts_at + KHAN_REVEAL_LEAD
    )
    return DrawTimeline(starts_at, reveal_at, ends_at)


def fast_presentation_timeline(
    scheduled_at: datetime,
    executed_at: datetime | None,
    number_count: int,
) -> DrawTimeline:
    """Return a compact reveal timeline for the three-number Fast draw."""
    starts_at = max(scheduled_at, executed_at) if executed_at else scheduled_at
    reveal_at = tuple(
        starts_at + FAST_REVEAL_LEAD + FAST_REVEAL_INTERVAL * index
        for index in range(number_count)
    )
    ends_at = (
        reveal_at[-1] + FAST_REVEAL_INTERVAL
        if reveal_at
        else starts_at + FAST_REVEAL_LEAD
    )
    return DrawTimeline(starts_at, reveal_at, ends_at)


def sales_status(
    *,
    now: datetime,
    status: DrawStatus,
    sales_close_at: datetime,
    timeline: DrawTimeline,
) -> str:
    if status == DrawStatus.COMPLETED:
        return "COMPLETED"
    if now >= timeline.starts_at or status in {DrawStatus.DRAWING, DrawStatus.SETTLING}:
        return "DRAWING"
    if now >= sales_close_at or status in {DrawStatus.CLOSED, DrawStatus.FAILED}:
        return "CLOSED"
    if sales_close_at - now <= CUTOFF_SOON:
        return "CLOSING_SOON"
    return "OPEN"
