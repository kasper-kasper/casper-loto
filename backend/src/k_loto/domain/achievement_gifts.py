"""Gift-only limits: preserve player caps and never buy a complete outcome space."""

from math import comb
from typing import Any

from k_loto.domain.bingo import POOL_SIZE
from k_loto.domain.lottery_rules import get_lottery_rules


def combination_count(ruleset: str) -> int:
    rules = get_lottery_rules(ruleset)
    if rules.ordered:
        return int(
            (rules.max_number - rules.minimum_number + 1) ** rules.numbers_to_pick
        )
    if rules.secondary_numbers_to_pick:
        assert (
            rules.primary_max_number is not None
            and rules.primary_numbers_to_pick is not None
        )
        return (
            comb(rules.primary_max_number, rules.primary_numbers_to_pick)
            * comb(rules.secondary_max_number, rules.secondary_numbers_to_pick)
            * (rules.server_code_max or 1)
        )
    return comb(rules.max_number - rules.minimum_number + 1, rules.numbers_to_pick)


def gift_draw_capacity(lottery: Any) -> int:
    cap = min(
        lottery.max_tickets_per_user_per_draw,
        combination_count(lottery.ruleset_code) - 1,
    )
    return int(min(cap, POOL_SIZE - 1) if lottery.code == "bingo" else cap)
