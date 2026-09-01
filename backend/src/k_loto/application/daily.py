"""Transactional Daily purchase and settlement services."""

from k_loto.application.weekly import (
    WeeklySettlementService,
    WeeklyTicketPurchaseService,
)
from k_loto.domain.daily import calculate_daily_settlement, quote_daily_purchase
from k_loto.domain.enums import LotteryKind
from k_loto.domain.lottery_rules import DAILY_RULES


class DailyTicketPurchaseService(WeeklyTicketPurchaseService):
    lottery_kind = LotteryKind.DAILY
    numbers_to_pick = 4
    max_number = 15
    quote_purchase = staticmethod(quote_daily_purchase)
    lottery_label = "Daily"
    default_lottery_code = "daily"
    ruleset_code = DAILY_RULES.code


class DailySettlementService(WeeklySettlementService):
    lottery_kind = LotteryKind.DAILY
    numbers_to_pick = 4
    max_number = 15
    calculate_settlement = staticmethod(calculate_daily_settlement)
    lottery_label = "Daily"
    ruleset_code = DAILY_RULES.code
