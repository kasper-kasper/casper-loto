"""Pure Weekly 5/20 validation, purchase and settlement mathematics."""

import secrets
from dataclasses import dataclass
from uuid import UUID

from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InsufficientReserve,
    InvalidTicket,
)

WEEKLY_MAX_NUMBER = 20
WEEKLY_NUMBERS_TO_PICK = 5


@dataclass(frozen=True, slots=True)
class PurchaseQuote:
    combinations: tuple[tuple[int, ...], ...]
    total_cost: int
    jackpot_contribution: int
    distribution_contribution: int


@dataclass(frozen=True, slots=True)
class SettlementTicket:
    id: UUID
    public_number: int
    user_id: UUID
    numbers: tuple[int, ...]
    purchase_price: int


@dataclass(frozen=True, slots=True)
class TicketPayout:
    ticket_id: UUID
    public_number: int
    user_id: UUID
    matches: int
    amount: int


@dataclass(frozen=True, slots=True)
class WeeklySettlementPlan:
    winning_numbers: tuple[int, ...]
    payouts: tuple[TicketPayout, ...]
    distribution_opening: int
    distribution_closing: int
    reserve_used: int
    jackpot_opening: int
    jackpot_closing: int
    jackpot_reset_credit: int
    total_payout: int

    @property
    def jackpot_won(self) -> bool:
        return any(item.matches == 5 for item in self.payouts)


class SystemRandomNumberGenerator:
    """Cryptographically secure official draw generator."""

    def __init__(self) -> None:
        self._random = secrets.SystemRandom()

    def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]:
        if numbers_to_pick <= 0 or population_size < numbers_to_pick:
            raise ValueError("Invalid draw population configuration.")
        return tuple(
            sorted(self._random.sample(range(1, population_size + 1), numbers_to_pick))
        )


def validate_weekly_combination(
    numbers: tuple[int, ...] | list[int],
) -> tuple[int, ...]:
    """Return a canonical Weekly combination or raise a domain error."""
    if len(numbers) != WEEKLY_NUMBERS_TO_PICK:
        raise InvalidTicket("Weekly tickets require exactly 5 numbers.")
    if len(set(numbers)) != WEEKLY_NUMBERS_TO_PICK:
        raise InvalidTicket("Ticket numbers must be unique.")
    if any(
        isinstance(number, bool) or not isinstance(number, int) for number in numbers
    ):
        raise InvalidTicket("Ticket numbers must be integers.")
    if any(number < 1 or number > WEEKLY_MAX_NUMBER for number in numbers):
        raise InvalidTicket("Weekly ticket numbers must be between 1 and 20.")
    return tuple(sorted(numbers))


def quote_weekly_purchase(
    combinations: list[list[int] | tuple[int, ...]],
    ticket_price: int,
    balance: int,
) -> PurchaseQuote:
    """Validate an atomic multi-ticket purchase and calculate its CAS split."""
    if not combinations:
        raise InvalidTicket("At least one ticket is required.")
    if ticket_price <= 0 or ticket_price % 4 != 0:
        raise ConfigurationError(
            "Weekly ticket price must be positive and divisible by 4 CAS."
        )
    canonical = tuple(validate_weekly_combination(item) for item in combinations)
    total_cost = ticket_price * len(canonical)
    if balance < total_cost:
        raise InsufficientBalance("Insufficient CAS balance.")
    half = total_cost // 2
    return PurchaseQuote(canonical, total_cost, half, half)


def _allocate_evenly(
    pool: int,
    tickets: list[SettlementTicket],
) -> dict[UUID, int]:
    """Allocate whole CAS deterministically, assigning remainders by ticket number."""
    if not tickets:
        return {}
    ordered = sorted(tickets, key=lambda ticket: (ticket.public_number, ticket.id.int))
    quotient, remainder = divmod(pool, len(ordered))
    return {
        ticket.id: quotient + (1 if index < remainder else 0)
        for index, ticket in enumerate(ordered)
    }


def calculate_weekly_settlement(
    tickets: list[SettlementTicket],
    winning_numbers: tuple[int, ...] | list[int],
    *,
    distribution_balance: int,
    jackpot_balance: int,
    reserve_balance: int,
    base_jackpot: int,
) -> WeeklySettlementPlan:
    """Calculate a complete Weekly settlement without mutating external state."""
    winning = validate_weekly_combination(winning_numbers)
    if min(distribution_balance, jackpot_balance, reserve_balance, base_jackpot) < 0:
        raise ConfigurationError("Lottery account balances cannot be negative.")

    matches: dict[UUID, int] = {}
    for ticket in tickets:
        validate_weekly_combination(ticket.numbers)
        if ticket.purchase_price <= 0 or ticket.purchase_price % 4 != 0:
            raise ConfigurationError(
                "Ticket price snapshot must be divisible by 4 CAS."
            )
        matches[ticket.id] = len(set(ticket.numbers).intersection(winning))

    guaranteed: dict[UUID, int] = {}
    for ticket in tickets:
        match_count = matches[ticket.id]
        if match_count == 2:
            guaranteed[ticket.id] = ticket.purchase_price // 4
        elif match_count == 3:
            guaranteed[ticket.id] = ticket.purchase_price

    guaranteed_total = sum(guaranteed.values())
    reserve_used = max(guaranteed_total - distribution_balance, 0)
    if reserve_used > reserve_balance:
        raise InsufficientReserve(
            "Distribution fund and reserve cannot cover guaranteed payouts."
        )
    distribution_after_guaranteed = max(distribution_balance - guaranteed_total, 0)

    four_match_tickets = [ticket for ticket in tickets if matches[ticket.id] == 4]
    four_match_payouts = _allocate_evenly(
        distribution_after_guaranteed, four_match_tickets
    )
    distribution_closing = 0 if four_match_tickets else distribution_after_guaranteed

    five_match_tickets = [ticket for ticket in tickets if matches[ticket.id] == 5]
    jackpot_payouts = _allocate_evenly(jackpot_balance, five_match_tickets)
    jackpot_reset_credit = base_jackpot if five_match_tickets else 0
    jackpot_closing = base_jackpot if five_match_tickets else jackpot_balance

    payouts = tuple(
        TicketPayout(
            ticket_id=ticket.id,
            public_number=ticket.public_number,
            user_id=ticket.user_id,
            matches=matches[ticket.id],
            amount=(
                guaranteed.get(ticket.id, 0)
                + four_match_payouts.get(ticket.id, 0)
                + jackpot_payouts.get(ticket.id, 0)
            ),
        )
        for ticket in sorted(
            tickets, key=lambda item: (item.public_number, item.id.int)
        )
    )
    return WeeklySettlementPlan(
        winning_numbers=winning,
        payouts=payouts,
        distribution_opening=distribution_balance,
        distribution_closing=distribution_closing,
        reserve_used=reserve_used,
        jackpot_opening=jackpot_balance,
        jackpot_closing=jackpot_closing,
        jackpot_reset_credit=jackpot_reset_credit,
        total_payout=sum(item.amount for item in payouts),
    )
