"""Backward-compatible Weekly 5/20 API backed by declarative rules."""

from k_loto.domain.lottery_rules import (
    WEEKLY_RULES,
    PurchaseQuote,
    SettlementPlan,
    SettlementTicket,
    SystemRandomNumberGenerator,
    TicketPayout,
    _allocate_evenly,
)

WEEKLY_MAX_NUMBER = WEEKLY_RULES.max_number
WEEKLY_NUMBERS_TO_PICK = WEEKLY_RULES.numbers_to_pick
WeeklySettlementPlan = SettlementPlan
validate_weekly_combination = WEEKLY_RULES.validate_combination
quote_weekly_purchase = WEEKLY_RULES.quote_purchase
calculate_weekly_settlement = WEEKLY_RULES.calculate_settlement

__all__ = [
    "PurchaseQuote",
    "SettlementTicket",
    "SystemRandomNumberGenerator",
    "TicketPayout",
    "WeeklySettlementPlan",
    "_allocate_evenly",
    "calculate_weekly_settlement",
    "quote_weekly_purchase",
    "validate_weekly_combination",
]
