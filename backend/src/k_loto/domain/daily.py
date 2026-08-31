"""Pure Daily 4/15 validation, purchase and settlement mathematics."""

from uuid import UUID

from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InsufficientReserve,
    InvalidTicket,
)
from k_loto.domain.weekly import (
    PurchaseQuote,
    SettlementTicket,
    TicketPayout,
    WeeklySettlementPlan,
    _allocate_evenly,
)

DAILY_MAX_NUMBER = 15
DAILY_NUMBERS_TO_PICK = 4


def validate_daily_combination(
    numbers: tuple[int, ...] | list[int],
) -> tuple[int, ...]:
    if len(numbers) != DAILY_NUMBERS_TO_PICK:
        raise InvalidTicket("Daily tickets require exactly 4 numbers.")
    if len(set(numbers)) != DAILY_NUMBERS_TO_PICK:
        raise InvalidTicket("Ticket numbers must be unique.")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in numbers):
        raise InvalidTicket("Ticket numbers must be integers.")
    if any(value < 1 or value > DAILY_MAX_NUMBER for value in numbers):
        raise InvalidTicket("Daily ticket numbers must be between 1 and 15.")
    return tuple(sorted(numbers))


def quote_daily_purchase(
    combinations: list[list[int] | tuple[int, ...]], ticket_price: int, balance: int
) -> PurchaseQuote:
    if not combinations:
        raise InvalidTicket("At least one ticket is required.")
    if ticket_price <= 0 or ticket_price % 2:
        raise ConfigurationError("Daily ticket price must be positive and even.")
    canonical = tuple(validate_daily_combination(item) for item in combinations)
    total_cost = ticket_price * len(canonical)
    if balance < total_cost:
        raise InsufficientBalance("Insufficient CAS balance.")
    jackpot = total_cost * 4 // 10
    return PurchaseQuote(canonical, total_cost, jackpot, total_cost - jackpot)


def calculate_daily_settlement(
    tickets: list[SettlementTicket],
    winning_numbers: tuple[int, ...] | list[int],
    *,
    distribution_balance: int,
    jackpot_balance: int,
    reserve_balance: int,
    base_jackpot: int,
) -> WeeklySettlementPlan:
    winning = validate_daily_combination(winning_numbers)
    if min(distribution_balance, jackpot_balance, reserve_balance, base_jackpot) < 0:
        raise ConfigurationError("Lottery account balances cannot be negative.")

    matches: dict[UUID, int] = {}
    guaranteed: dict[UUID, int] = {}
    for ticket in tickets:
        validate_daily_combination(ticket.numbers)
        if ticket.purchase_price <= 0 or ticket.purchase_price % 2:
            raise ConfigurationError(
                "Daily ticket price snapshot must be positive and even."
            )
        match_count = len(set(ticket.numbers).intersection(winning))
        matches[ticket.id] = match_count
        if match_count == 2:
            guaranteed[ticket.id] = ticket.purchase_price // 2
        elif match_count == 3:
            guaranteed[ticket.id] = ticket.purchase_price * 3

    guaranteed_total = sum(guaranteed.values())
    reserve_used = max(guaranteed_total - distribution_balance, 0)
    if reserve_used > reserve_balance:
        raise InsufficientReserve(
            "Distribution fund and reserve cannot cover guaranteed payouts."
        )
    distribution_closing = max(distribution_balance - guaranteed_total, 0)

    jackpot_tickets = [ticket for ticket in tickets if matches[ticket.id] == 4]
    jackpot_payouts = _allocate_evenly(jackpot_balance, jackpot_tickets)
    jackpot_reset_credit = base_jackpot if jackpot_tickets else 0
    jackpot_closing = base_jackpot if jackpot_tickets else jackpot_balance
    payouts = tuple(
        TicketPayout(
            ticket.id,
            ticket.public_number,
            ticket.user_id,
            matches[ticket.id],
            guaranteed.get(ticket.id, 0) + jackpot_payouts.get(ticket.id, 0),
        )
        for ticket in sorted(
            tickets, key=lambda item: (item.public_number, item.id.int)
        )
    )
    return WeeklySettlementPlan(
        winning,
        payouts,
        distribution_balance,
        distribution_closing,
        reserve_used,
        jackpot_balance,
        jackpot_closing,
        jackpot_reset_credit,
        sum(item.amount for item in payouts),
        4,
    )
