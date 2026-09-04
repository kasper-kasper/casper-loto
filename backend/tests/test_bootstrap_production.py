"""Regression checks for idempotent production bootstrap settings."""

from scripts.bootstrap_production import FAST_SALES_CUTOFF_SECONDS, fast_schedule


def test_fast_bootstrap_preserves_eight_second_cutoff() -> None:
    schedule = fast_schedule("00:03")

    assert schedule["anchor_time"] == "00:03"
    assert schedule["sales_cutoff_seconds"] == FAST_SALES_CUTOFF_SECONDS == 8
    assert schedule["future_draw_count"] == 2
