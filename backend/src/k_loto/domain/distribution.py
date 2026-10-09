"""Owner-approved jackpot roll-down; ordinary prizes remain unchanged."""

from dataclasses import replace
from typing import cast

from k_loto.domain.errors import InsufficientReserve
from k_loto.domain.lottery_rules import (
    LotteryRuleStrategy,
    SettlementPlan,
    SettlementTicket,
    _allocate_evenly,
)


def distribute_jackpot(
    plan: SettlementPlan,
    tickets: list[SettlementTicket],
    rules: LotteryRuleStrategy,
    *,
    base_jackpot: int,
    fund_balance: int,
) -> SettlementPlan:
    if not tickets or plan.jackpot_won or plan.jackpot_opening == 0:
        return plan
    selected = []
    category = "all"
    if rules.code == "bingo_12_60":
        for tour in (1, 0):
            ids = {
                p.ticket_id
                for p in plan.payouts
                if p.bingo_result
                and cast(list[int], p.bingo_result["amounts"])[tour] > 0
            }
            selected = [t for t in tickets if t.id in ids]
            if selected:
                category = f"bingo-tour-{tour + 1}"
                break
    else:
        categories = sorted(
            set(rules.fixed_payouts)
            | set(rules.guaranteed_payouts)
            | set(rules.tier_pool_payouts),
            reverse=True,
        )
        matches = {p.ticket_id: p.matches for p in plan.payouts}
        for count in categories:
            selected = [t for t in tickets if matches[t.id] == count]
            if selected:
                category = str(count)
                break
    if not selected:
        selected = tickets
    used = plan.reserve_used + base_jackpot
    if used > fund_balance:
        raise InsufficientReserve("Kasper Fund cannot restore the distributed jackpot.")
    shares = _allocate_evenly(plan.jackpot_opening, selected)
    return replace(
        plan,
        payouts=tuple(
            replace(
                p,
                amount=p.amount + shares.get(p.ticket_id, 0),
                jackpot_amount=shares.get(p.ticket_id, 0),
            )
            for p in plan.payouts
        ),
        jackpot_closing=base_jackpot,
        jackpot_reset_credit=base_jackpot,
        reserve_used=used,
        total_payout=plan.total_payout + plan.jackpot_opening,
        jackpot_distributed=True,
        distribution_category=category,
    )
