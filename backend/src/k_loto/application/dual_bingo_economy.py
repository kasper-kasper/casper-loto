"""Approved fixed Dual and per-card Bingo economy; applied only at final release."""

from k_loto.application.economy_batches import PausedEconomyBatchService
from k_loto.domain.dual import DUAL_ECONOMY_MAX_PRIZE, DUAL_ECONOMY_PRICE
from k_loto.domain.lottery_rules import BINGO_ECONOMY_RULES, DUAL_ECONOMY_RULES


class DualEconomyService(PausedEconomyBatchService):
    step = "2026-10-dual-economy-v2"
    # Dual's existing account displays the fixed maximum; ticket purchases never
    # accumulate into it. All stakes and payouts go through the Kasper Fund.
    terms = (("dual", DUAL_ECONOMY_RULES, DUAL_ECONOMY_PRICE, DUAL_ECONOMY_MAX_PRIZE),)
    per_draw_limit = 50


class BingoEconomyService(PausedEconomyBatchService):
    step = "2026-10-bingo-economy-v2"
    terms = (("bingo", BINGO_ECONOMY_RULES, 50_000, 1_000_000_000),)
    per_draw_limit = 75
    per_purchase_limit = 75
