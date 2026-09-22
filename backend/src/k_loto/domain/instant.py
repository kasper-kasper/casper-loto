"""Fixed Kasper LIVE odds and prize selection."""

from dataclasses import dataclass

TICKET_PRICE = 2_000
ODDS_VERSION = "kasper-live-v1"
SYMBOL_COUNT = 3
SYMBOL_VARIANTS = 8


@dataclass(frozen=True, slots=True)
class PrizeBand:
    upper_roll: int
    prize: int


PRIZE_BANDS = (
    PrizeBand(7_000, 0),
    PrizeBand(8_500, 1_000),
    PrizeBand(9_300, 2_000),
    PrizeBand(9_800, 5_000),
    PrizeBand(9_980, 20_000),
    PrizeBand(9_999, 100_000),
    PrizeBand(10_000, 1_000_000),
)


def prize_for_roll(roll: int) -> int:
    """Map one uniform 1..10,000 roll to the agreed prize table."""
    if not 1 <= roll <= 10_000:
        raise ValueError("Kasper LIVE roll must be between 1 and 10,000.")
    return next(band.prize for band in PRIZE_BANDS if roll <= band.upper_roll)
