"""Approved 2:22/Halloween/September batch for the planned pause."""

from k_loto.application.economy_batches import PausedEconomyBatchService
from k_loto.domain.lottery_rules import (
    HALLOWEEN_ECONOMY_RULES,
    PLL_ECONOMY_RULES,
    SEPTEMBER_ECONOMY_RULES,
)

STEP = "2026-10-themed-economy-v2"
TERMS = (
    ("pll", PLL_ECONOMY_RULES, 22_222, 2_222_222),
    ("grob", HALLOWEEN_ECONOMY_RULES, 6_666, 6_666_666),
    ("september", SEPTEMBER_ECONOMY_RULES, 3_333, 3_333_333),
)


class ThemedEconomyService(PausedEconomyBatchService):
    step = STEP
    terms = TERMS
    per_draw_limit = 100
