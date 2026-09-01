"""Backward-compatible Daily 4/15 API backed by declarative rules."""

from k_loto.domain.lottery_rules import DAILY_RULES

DAILY_MAX_NUMBER = DAILY_RULES.max_number
DAILY_NUMBERS_TO_PICK = DAILY_RULES.numbers_to_pick
validate_daily_combination = DAILY_RULES.validate_combination
quote_daily_purchase = DAILY_RULES.quote_purchase
calculate_daily_settlement = DAILY_RULES.calculate_settlement
