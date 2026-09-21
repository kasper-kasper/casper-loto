"""Regression checks for idempotent production bootstrap settings."""

from scripts.bootstrap_production import (
    FAST_LOTTERY_FORMATS,
    FAST_SALES_CUTOFF_SECONDS,
    fast_schedule,
)


def test_fast_bootstrap_preserves_eight_second_cutoff() -> None:
    schedule = fast_schedule("00:03")

    assert schedule["anchor_time"] == "00:03"
    assert schedule["sales_cutoff_seconds"] == FAST_SALES_CUTOFF_SECONDS == 8
    assert schedule["future_draw_count"] == 2


def test_fast_bootstrap_uses_current_flash_and_pulse_formats() -> None:
    formats = {item[0]: item[3:] for item in FAST_LOTTERY_FORMATS}

    assert formats["flash"] == ("fast_3_20", 3, 20)
    assert formats["pulse"] == ("pulse_2_12_2_6", 4, 18)
