"""Declarative, reusable lottery purchase and payout strategies."""

import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import UUID

from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InsufficientReserve,
    InvalidTicket,
)


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
class SettlementPlan:
    winning_numbers: tuple[int, ...]
    payouts: tuple[TicketPayout, ...]
    distribution_opening: int
    distribution_closing: int
    reserve_used: int
    jackpot_opening: int
    jackpot_closing: int
    jackpot_reset_credit: int
    total_payout: int
    jackpot_match_count: int

    @property
    def jackpot_won(self) -> bool:
        return any(item.matches == self.jackpot_match_count for item in self.payouts)


@dataclass(frozen=True, slots=True)
class PayoutRatio:
    numerator: int
    denominator: int = 1

    def apply(self, amount: int) -> int:
        return amount * self.numerator // self.denominator


@dataclass(frozen=True, slots=True)
class LotteryRuleStrategy:
    """Complete format and payout rules without transport or database concerns."""

    code: str
    label: str
    numbers_to_pick: int
    max_number: int
    price_divisor: int
    jackpot_share: PayoutRatio
    guaranteed_payouts: Mapping[int, PayoutRatio]
    distribution_pool_match: int | None
    jackpot_match: int
    fixed_payouts: Mapping[int, int] = field(
        default_factory=lambda: MappingProxyType({})
    )
    jackpot_refill_from_reserve: bool = False

    def validate_combination(
        self, numbers: tuple[int, ...] | list[int]
    ) -> tuple[int, ...]:
        if len(numbers) != self.numbers_to_pick:
            raise InvalidTicket(
                f"{self.label} tickets require exactly {self.numbers_to_pick} numbers."
            )
        if len(set(numbers)) != self.numbers_to_pick:
            raise InvalidTicket("Ticket numbers must be unique.")
        if any(
            isinstance(value, bool) or not isinstance(value, int) for value in numbers
        ):
            raise InvalidTicket("Ticket numbers must be integers.")
        if any(value < 1 or value > self.max_number for value in numbers):
            raise InvalidTicket(
                f"{self.label} ticket numbers must be between 1 and {self.max_number}."
            )
        return tuple(sorted(numbers))

    def quote_purchase(
        self,
        combinations: list[list[int] | tuple[int, ...]],
        ticket_price: int,
        balance: int,
    ) -> PurchaseQuote:
        if not combinations:
            raise InvalidTicket("At least one ticket is required.")
        if ticket_price <= 0 or ticket_price % self.price_divisor:
            raise ConfigurationError(
                f"{self.label} ticket price must be positive and divisible by "
                f"{self.price_divisor} CAS."
            )
        canonical = tuple(self.validate_combination(item) for item in combinations)
        total_cost = ticket_price * len(canonical)
        if balance < total_cost:
            raise InsufficientBalance("Insufficient CAS balance.")
        # Split every ticket independently so integer rounding never depends on
        # whether equal tickets were bought separately or in one bulk request.
        jackpot = self.jackpot_share.apply(ticket_price) * len(canonical)
        return PurchaseQuote(canonical, total_cost, jackpot, total_cost - jackpot)

    def calculate_settlement(
        self,
        tickets: list[SettlementTicket],
        winning_numbers: tuple[int, ...] | list[int],
        *,
        distribution_balance: int,
        jackpot_balance: int,
        reserve_balance: int,
        base_jackpot: int,
    ) -> SettlementPlan:
        winning = self.validate_combination(winning_numbers)
        if (
            min(distribution_balance, jackpot_balance, reserve_balance, base_jackpot)
            < 0
        ):
            raise ConfigurationError("Lottery account balances cannot be negative.")
        matches: dict[UUID, int] = {}
        guaranteed: dict[UUID, int] = {}
        for ticket in tickets:
            self.validate_combination(ticket.numbers)
            if ticket.purchase_price <= 0 or ticket.purchase_price % self.price_divisor:
                raise ConfigurationError(
                    "Ticket price snapshot is incompatible with the lottery rules."
                )
            count = len(set(ticket.numbers).intersection(winning))
            matches[ticket.id] = count
            fixed = self.fixed_payouts.get(count)
            ratio = self.guaranteed_payouts.get(count)
            if fixed is not None:
                if fixed < 0:
                    raise ConfigurationError("Fixed payouts cannot be negative.")
                guaranteed[ticket.id] = fixed
            elif ratio is not None:
                guaranteed[ticket.id] = ratio.apply(ticket.purchase_price)
        guaranteed_total = sum(guaranteed.values())
        distribution_shortfall = max(guaranteed_total - distribution_balance, 0)
        jackpot_tickets = [
            ticket for ticket in tickets if matches[ticket.id] == self.jackpot_match
        ]
        jackpot_reset_credit = base_jackpot if jackpot_tickets else 0
        reserve_used = distribution_shortfall + (
            jackpot_reset_credit if self.jackpot_refill_from_reserve else 0
        )
        if reserve_used > reserve_balance:
            raise InsufficientReserve(
                "Lottery funds and reserve cannot cover all payouts and refills."
            )
        distribution_after = max(distribution_balance - guaranteed_total, 0)
        distribution_tickets = (
            [
                ticket
                for ticket in tickets
                if matches[ticket.id] == self.distribution_pool_match
            ]
            if self.distribution_pool_match is not None
            else []
        )
        distribution_payouts = _allocate_evenly(
            distribution_after, distribution_tickets
        )
        distribution_closing = 0 if distribution_tickets else distribution_after
        jackpot_payouts = _allocate_evenly(jackpot_balance, jackpot_tickets)
        jackpot_closing = base_jackpot if jackpot_tickets else jackpot_balance
        payouts = tuple(
            TicketPayout(
                ticket.id,
                ticket.public_number,
                ticket.user_id,
                matches[ticket.id],
                guaranteed.get(ticket.id, 0)
                + distribution_payouts.get(ticket.id, 0)
                + jackpot_payouts.get(ticket.id, 0),
            )
            for ticket in sorted(
                tickets, key=lambda item: (item.public_number, item.id.int)
            )
        )
        return SettlementPlan(
            winning,
            payouts,
            distribution_balance,
            distribution_closing,
            reserve_used,
            jackpot_balance,
            jackpot_closing,
            jackpot_reset_credit,
            sum(item.amount for item in payouts),
            self.jackpot_match,
        )


def _allocate_evenly(pool: int, tickets: list[SettlementTicket]) -> dict[UUID, int]:
    if not tickets:
        return {}
    ordered = sorted(tickets, key=lambda ticket: (ticket.public_number, ticket.id.int))
    quotient, remainder = divmod(pool, len(ordered))
    return {
        ticket.id: quotient + (1 if index < remainder else 0)
        for index, ticket in enumerate(ordered)
    }


class SystemRandomNumberGenerator:
    def __init__(self) -> None:
        self._random = secrets.SystemRandom()

    def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]:
        if numbers_to_pick <= 0 or population_size < numbers_to_pick:
            raise ValueError("Invalid draw population configuration.")
        return tuple(
            sorted(self._random.sample(range(1, population_size + 1), numbers_to_pick))
        )


WEEKLY_RULES = LotteryRuleStrategy(
    "weekly_5_20",
    "Weekly",
    5,
    20,
    4,
    PayoutRatio(1, 2),
    MappingProxyType({2: PayoutRatio(1, 4), 3: PayoutRatio(1)}),
    4,
    5,
)
DAILY_RULES = LotteryRuleStrategy(
    "daily_4_15",
    "Daily",
    4,
    15,
    2,
    PayoutRatio(2, 5),
    MappingProxyType({2: PayoutRatio(1, 2), 3: PayoutRatio(3)}),
    None,
    4,
)
SEPTEMBER_RULES = LotteryRuleStrategy(
    "september_3_33",
    "3 СЕНТЯБРЯ",
    3,
    33,
    1,
    PayoutRatio(0),
    MappingProxyType({}),
    None,
    3,
    MappingProxyType({1: 333, 2: 3_333}),
    True,
)
GROB_RULES = LotteryRuleStrategy(
    "grob_3_16",
    "ГРОБ",
    3,
    16,
    1,
    PayoutRatio(2, 5),
    MappingProxyType({}),
    None,
    3,
    MappingProxyType({1: 666, 2: 6_666}),
)
LOTTERY_RULES: Mapping[str, LotteryRuleStrategy] = MappingProxyType(
    {
        rule.code: rule
        for rule in (WEEKLY_RULES, DAILY_RULES, SEPTEMBER_RULES, GROB_RULES)
    }
)


def get_lottery_rules(code: str) -> LotteryRuleStrategy:
    try:
        return LOTTERY_RULES[code]
    except KeyError as error:
        raise ConfigurationError(f"Unknown lottery rule strategy: {code!r}.") from error
