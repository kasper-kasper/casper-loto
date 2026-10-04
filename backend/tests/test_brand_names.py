"""Brand presentation regression checks; no purchases or database writes."""

import pytest

from k_loto.infrastructure.brand_names import display_brand_name
from k_loto.infrastructure.telegram_messages import format_inactivity_reminder


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Kasper Grand", "Casper Grand"),
        ("Kasper Bingo", "Casper Bingo"),
        ("KASPER LIVE", "CASPER LIVE"),
        ("Caster Loto", "Casper Loto"),
        ("Casper Lotto", "Casper Loto"),
        ("K-Loto", "Casper Loto"),
        ("ПЛЛ-Лото", "2:22"),
        ("6 из 36", "6 из 36"),
        ("Каспер Лото", "Каспер Лото"),
    ],
)
def test_display_brand_name(source: str, expected: str) -> None:
    assert display_brand_name(source) == expected


def test_bot_formats_the_label_without_changing_notification_payload() -> None:
    payload = {
        "lottery_name": "Kasper Bingo",
        "lottery_code": "bingo",
        "draw_number": 123,
        "scheduled_at": "2026-10-04T19:00:00+00:00",
    }
    message = format_inactivity_reminder(payload)
    assert "Casper Bingo №0123" in message
    assert "04.10.2026 · 22:00 МСК" in message
    assert payload["lottery_name"] == "Kasper Bingo"
