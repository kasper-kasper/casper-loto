"""Fixed Kasper LIVE odds and prize selection."""

from dataclasses import dataclass

TICKET_PRICE = 2_000
ODDS_VERSION = "kasper-live-v1"
SYMBOL_COUNT = 3
SYMBOL_VARIANTS = 8
# The visual combination is part of the result: three different symbols mean
# no prize; a repeated symbol identifies the winning category.
PRIZE_SYMBOLS = {
    0: (1, 2, 3),
    1_000: (2, 2, 2),
    2_000: (3, 3, 3),
    5_000: (4, 4, 4),
    20_000: (5, 5, 5),
    100_000: (6, 6, 6),
    1_000_000: (7, 7, 7),
}


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


def symbols_for_prize(prize: int) -> tuple[int, ...]:
    """Return the visual code that makes the win/loss legible to a player."""
    try:
        return PRIZE_SYMBOLS[prize]
    except KeyError as error:
        raise ValueError("Unknown Kasper LIVE prize category.") from error


@dataclass(frozen=True, slots=True)
class InstantRules:
    code: str
    name: str
    price: int
    version: str
    bands: tuple[PrizeBand, ...]

    def prize(self, roll: int) -> int:
        if not 1 <= roll <= 10_000:
            raise ValueError("Instant roll must be between 1 and 10,000.")
        return next(band.prize for band in self.bands if roll <= band.upper_roll)

    def symbols(self, prize: int) -> tuple[int, ...]:
        for index, band in enumerate(self.bands):
            if band.prize == prize:
                return (1, 2, 3) if prize == 0 else (index + 1,) * 3
        raise ValueError("Unknown instant prize category.")


LIVE_RULES = InstantRules(
    "kasper-live", "Casper LIVE", TICKET_PRICE, ODDS_VERSION, PRIZE_BANDS
)
AURORA_RULES = InstantRules(
    "aurora",
    "Casper Aurora",
    3_000,
    "casper-aurora-v1",
    (
        PrizeBand(6_000, 0),
        PrizeBand(8_000, 2_000),
        PrizeBand(9_000, 3_000),
        PrizeBand(9_700, 6_000),
        PrizeBand(9_980, 25_000),
        PrizeBand(9_999, 200_000),
        PrizeBand(10_000, 1_000_000),
    ),
)
INSTANT_GAMES = {rules.code: rules for rules in (LIVE_RULES, AURORA_RULES)}


def instant_rules(code: str) -> InstantRules:
    try:
        return INSTANT_GAMES[code]
    except KeyError as error:
        raise ValueError("Unknown instant game.") from error


def instant_rules_for_version(version: str) -> InstantRules:
    for rules in INSTANT_GAMES.values():
        if rules.version == version:
            return rules
    raise ValueError("Unknown instant odds version.")
