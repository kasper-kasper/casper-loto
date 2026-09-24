"""Casper Dual round and prize rules; draws remain the schedule authority."""

from datetime import datetime
from zoneinfo import ZoneInfo

from k_loto.domain.errors import ConfigurationError

MOSCOW = ZoneInfo("Europe/Moscow")
DUAL_PRICE = 20_000
DUAL_JACKPOT = 5_000_000
DUAL_PAYOUTS = {11: 10_000, 12: 100_000, 21: 100_000, 22: DUAL_JACKPOT}


def dual_phase(scheduled_at: datetime) -> str:
    local = scheduled_at.astimezone(MOSCOW)
    slot = (local.hour, local.minute)
    if slot == (0, 30):
        return "NIGHT"
    if slot == (7, 30):
        return "DAWN"
    raise ConfigurationError("Casper Dual draw has an invalid Moscow slot.")


def dual_matches(
    numbers: tuple[int, ...] | list[int],
    winning: tuple[int, ...] | list[int],
    phase: str,
) -> int:
    offset = 0 if phase == "NIGHT" else 12
    chosen = {value - offset for value in numbers if offset < value <= offset + 12}
    return len(chosen.intersection(winning))


def dual_match_code(night_matches: int, dawn_matches: int) -> int:
    return night_matches * 10 + dawn_matches


def dual_prize(night_matches: int, dawn_matches: int) -> int:
    return DUAL_PAYOUTS.get(dual_match_code(night_matches, dawn_matches), 0)
