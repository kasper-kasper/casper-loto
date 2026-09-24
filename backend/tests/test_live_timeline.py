"""Authoritative live timeline and sales presentation states."""

from datetime import UTC, datetime, timedelta

from k_loto.domain.enums import DrawStatus
from k_loto.domain.live_timeline import (
    draw_timeline,
    fast_presentation_timeline,
    khan_presentation_timeline,
    presentation_timeline,
    sales_status,
)


def test_fast_timeline_reveals_three_numbers_in_three_and_a_half_seconds() -> None:
    starts_at = datetime(2026, 9, 4, 12, tzinfo=UTC)

    timeline = fast_presentation_timeline(starts_at, starts_at, 3)

    assert timeline.reveal_at == (
        starts_at + timedelta(milliseconds=500),
        starts_at + timedelta(milliseconds=1500),
        starts_at + timedelta(milliseconds=2500),
    )
    assert timeline.ends_at == starts_at + timedelta(milliseconds=3500)


def test_timeline_assigns_stable_reveal_moments() -> None:
    starts_at = datetime(2026, 9, 1, 9, tzinfo=UTC)
    timeline = draw_timeline(starts_at, 4)

    assert timeline.starts_at == starts_at
    assert timeline.reveal_at == tuple(
        starts_at + timedelta(seconds=1 + index * 2) for index in range(4)
    )
    assert timeline.ends_at == starts_at + timedelta(seconds=9)


def test_khan_timeline_runs_a_twenty_three_second_drum_show() -> None:
    starts_at = datetime(2026, 9, 1, 9, tzinfo=UTC)

    timeline = khan_presentation_timeline(starts_at, starts_at, 6)

    assert timeline.reveal_at[0] == starts_at + timedelta(seconds=4)
    assert timeline.reveal_at[-1] == starts_at + timedelta(seconds=27, milliseconds=500)
    assert timeline.ends_at == starts_at + timedelta(seconds=32, milliseconds=200)


def test_completed_draw_reveal_starts_when_result_is_ready() -> None:
    scheduled = datetime(2026, 9, 1, 9, tzinfo=UTC)
    executed = scheduled + timedelta(seconds=24)

    timeline = presentation_timeline(scheduled, executed, 4)

    assert timeline.starts_at == executed
    assert timeline.reveal_at[0] == executed + timedelta(seconds=1)


def test_sales_status_covers_owner_visible_lifecycle() -> None:
    starts_at = datetime(2026, 9, 1, 9, tzinfo=UTC)
    timeline = draw_timeline(starts_at, 4)
    cutoff = starts_at - timedelta(minutes=2)

    assert (
        sales_status(
            now=cutoff - timedelta(minutes=6),
            status=DrawStatus.SCHEDULED,
            sales_close_at=cutoff,
            timeline=timeline,
        )
        == "OPEN"
    )
    assert (
        sales_status(
            now=cutoff - timedelta(minutes=1),
            status=DrawStatus.SCHEDULED,
            sales_close_at=cutoff,
            timeline=timeline,
        )
        == "CLOSING_SOON"
    )
    assert (
        sales_status(
            now=cutoff,
            status=DrawStatus.SCHEDULED,
            sales_close_at=cutoff,
            timeline=timeline,
        )
        == "CLOSED"
    )
    assert (
        sales_status(
            now=starts_at,
            status=DrawStatus.DRAWING,
            sales_close_at=cutoff,
            timeline=timeline,
        )
        == "DRAWING"
    )
    assert (
        sales_status(
            now=starts_at,
            status=DrawStatus.COMPLETED,
            sales_close_at=cutoff,
            timeline=timeline,
        )
        == "COMPLETED"
    )
