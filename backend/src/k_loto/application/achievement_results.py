"""Adapt frozen settlement facts; never recalculate lottery payouts."""

from typing import Any

from k_loto.domain.instant import instant_rules_for_version
from k_loto.domain.lottery_rules import get_lottery_rules
from k_loto.infrastructure.database.models import Draw, InstantTicket, Lottery, Ticket


def ticket_result(ticket: Ticket, draw: Draw, lottery: Lottery) -> dict[str, Any]:
    ruleset = str(draw.configuration_snapshot.get("ruleset_code", lottery.ruleset_code))
    rules = get_lottery_rules(ruleset)
    categories = [f"matches.{ticket.matches}"] if ticket.prize_amount > 0 else []
    natural = (
        ticket.matches == rules.jackpot_match
        and ticket.prize_amount > 0
        and not draw.is_distribution
    )
    prizes = int(ticket.prize_amount > 0)
    primary = secondary = first_row = None
    full_card = None
    if ticket.matches is not None and rules.secondary_numbers_to_pick:
        divisor = 100 if rules.server_code_max else 10
        primary = ticket.matches // divisor
        secondary = (
            (ticket.matches // 10) % 10
            if rules.server_code_max
            else ticket.matches % 10
        )
    if ticket.bingo_result:
        moves = ticket.bingo_result.get("moves", [])
        first_row = min(moves) if moves else None
        full_card = max(moves) if len(moves) == 3 else None
        amounts = list(ticket.bingo_result.get("amounts", []))
        categories = [f"bingo.{i}" for i, value in enumerate(amounts) if value > 0]
        prizes = len(categories)
        natural = len(amounts) > 2 and amounts[2] > 0 and not draw.is_distribution
    return dict(
        lottery=lottery.code,
        prize=ticket.prize_amount,
        standard_price=int(
            draw.configuration_snapshot.get("ticket_price", ticket.purchase_price)
        ),
        paid=ticket.purchase_price,
        matches=ticket.matches,
        primary_matches=primary,
        secondary_matches=secondary,
        first_row_move=first_row,
        full_card_move=full_card,
        natural_jackpot=natural,
        categories=categories,
        prizes=prizes,
    )


def instant_result(ticket: InstantTicket) -> dict[str, Any]:
    rules = instant_rules_for_version(ticket.odds_version)
    return dict(
        lottery=rules.code,
        prize=ticket.prize_amount,
        standard_price=rules.price,
        paid=ticket.purchase_price,
        matches=None,
        natural_jackpot=False,
        categories=[f"instant.{ticket.prize_amount}"]
        if ticket.prize_amount > 0
        else [],
        prizes=int(ticket.prize_amount > 0),
    )
