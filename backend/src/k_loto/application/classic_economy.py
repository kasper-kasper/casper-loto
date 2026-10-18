"""Approved 6/36, Casper Ball and Casper Grand economy batch."""

from k_loto.application.economy_batches import PausedEconomyBatchService
from k_loto.domain.lottery_rules import (
    BALL_ECONOMY_RULES,
    CLASSIC_ECONOMY_RULES,
    GRAND_ECONOMY_RULES,
)

STEP = "2026-10-classic-ball-grand-economy-v2"
TERMS = (
    ("khan", CLASSIC_ECONOMY_RULES, 25_000, 100_000_000),
    ("pss", BALL_ECONOMY_RULES, 25_000, 250_000_000),
    ("weekly", GRAND_ECONOMY_RULES, 50_000, 5_000_000_000),
)


class ClassicEconomyService(PausedEconomyBatchService):
    step = STEP
    terms = TERMS
    per_draw_limit = 600
