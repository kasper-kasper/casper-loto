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

    assert formats["flash"] == ("fast_5_20_jackpot_only", 5, 20)
    assert formats["pulse"] == ("pulse_2_12_2_6_cipher_199", 5, 18)
    assert formats["shadow"] == ("code_5_digits", 5, 9)


async def test_draw_preparation_failure_does_not_prevent_api_bootstrap(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from scripts import bootstrap_production

    from k_loto.domain.enums import LotteryKind

    lottery = SimpleNamespace(id=uuid4(), is_active=True)

    class Session:
        values = iter([lottery, object(), object(), object()])

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def begin(self):
            return self

        async def scalar(self, statement):
            return next(self.values)

    prepare = AsyncMock(side_effect=RuntimeError("broken schedule"))
    monkeypatch.setattr(bootstrap_production, "session_factory", Session)
    monkeypatch.setattr(
        bootstrap_production.DrawScheduleService, "ensure_next_draw", prepare
    )
    await bootstrap_production.ensure_lottery(
        "weekly", "Grand", LotteryKind.WEEKLY, 7, 40, 5, {}, "grand_fixed_5_35_2_5"
    )
    prepare.assert_awaited_once()
