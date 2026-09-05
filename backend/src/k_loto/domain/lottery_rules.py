"""Declarative, reusable lottery purchase and payout strategies."""

import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol
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
    jackpot_amount: int | None = None
    bingo_result: dict[str, object] | None = None


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
        return any(
            (
                item.jackpot_amount > 0
                if item.jackpot_amount is not None
                else item.matches == self.jackpot_match_count
            )
            for item in self.payouts
        )


@dataclass(frozen=True, slots=True)
class PayoutRatio:
    numerator: int
    denominator: int = 1

    def apply(self, amount: int) -> int:
        return amount * self.numerator // self.denominator


class NumberGenerator(Protocol):
    def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]: ...


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
    primary_numbers_to_pick: int | None = None
    primary_max_number: int | None = None
    secondary_numbers_to_pick: int = 0
    secondary_max_number: int = 0
    secondary_storage_offset: int = 0
    tier_pool_payouts: Mapping[int, PayoutRatio] = field(
        default_factory=lambda: MappingProxyType({})
    )

    @property
    def display_primary_numbers_to_pick(self) -> int:
        return self.primary_numbers_to_pick or self.numbers_to_pick

    @property
    def display_primary_max_number(self) -> int:
        return self.primary_max_number or self.max_number

    def validate_combination(
        self, numbers: tuple[int, ...] | list[int]
    ) -> tuple[int, ...]:
        if self.code == "bingo_12_60":
            from k_loto.domain.bingo import validate_ticket

            return validate_ticket(numbers)
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
        if self.secondary_numbers_to_pick:
            primary = [
                value for value in numbers if value <= self.display_primary_max_number
            ]
            secondary = [
                value
                for value in numbers
                if self.secondary_storage_offset
                < value
                <= self.secondary_storage_offset + self.secondary_max_number
            ]
            if (
                len(primary) != self.display_primary_numbers_to_pick
                or len(secondary) != self.secondary_numbers_to_pick
                or len(primary) + len(secondary) != len(numbers)
            ):
                raise InvalidTicket(
                    f"{self.label} tickets require "
                    f"{self.display_primary_numbers_to_pick} main and "
                    f"{self.secondary_numbers_to_pick} special numbers."
                )
        return tuple(sorted(numbers))

    def generate_combination(self, generator: NumberGenerator) -> tuple[int, ...]:
        if self.code == "bingo_12_60":
            from k_loto.domain.bingo import generate_ticket

            return generate_ticket()
        if not self.secondary_numbers_to_pick:
            return generator.draw(self.max_number, self.numbers_to_pick)
        primary = generator.draw(
            self.display_primary_max_number, self.display_primary_numbers_to_pick
        )
        secondary = generator.draw(
            self.secondary_max_number, self.secondary_numbers_to_pick
        )
        return tuple(
            sorted(primary)
            + [self.secondary_storage_offset + value for value in sorted(secondary)]
        )

    def match_count(
        self, ticket_numbers: tuple[int, ...], winning_numbers: tuple[int, ...]
    ) -> int:
        if not self.secondary_numbers_to_pick:
            return len(set(ticket_numbers).intersection(winning_numbers))
        main_matches = len(
            {
                value
                for value in ticket_numbers
                if value <= self.display_primary_max_number
            }.intersection(
                value
                for value in winning_numbers
                if value <= self.display_primary_max_number
            )
        )
        special_matches = len(
            {
                value
                for value in ticket_numbers
                if value > self.secondary_storage_offset
            }.intersection(
                value
                for value in winning_numbers
                if value > self.secondary_storage_offset
            )
        )
        return main_matches * 10 + special_matches

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
        if self.code == "bingo_12_60":
            from k_loto.domain.bingo import outcomes

            results = outcomes(
                [(t.id, t.public_number, t.numbers) for t in tickets],
                tuple(winning_numbers),
                jackpot_balance,
            )
            won = any(r.amounts[2] > 0 for r in results.values())
            reset = base_jackpot if won else 0
            used = sum(sum(r.amounts[:2]) for r in results.values()) + reset
            if used > reserve_balance:
                raise InsufficientReserve("Kasper Fund cannot cover Bingo payouts.")
            payouts = tuple(
                TicketPayout(
                    t.id,
                    t.public_number,
                    t.user_id,
                    len(set(t.numbers).intersection(winning_numbers)),
                    sum(results[t.id].amounts),
                    results[t.id].amounts[2],
                    {
                        "moves": list(results[t.id].moves),
                        "amounts": list(results[t.id].amounts),
                    },
                )
                for t in tickets
            )
            return SettlementPlan(
                tuple(winning_numbers),
                payouts,
                0,
                0,
                used,
                jackpot_balance,
                base_jackpot if won else jackpot_balance,
                reset,
                sum(p.amount for p in payouts),
                12,
            )
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
            count = self.match_count(ticket.numbers, winning)
            matches[ticket.id] = count
            fixed = self.fixed_payouts.get(count)
            ratio = self.guaranteed_payouts.get(count)
            if fixed is not None:
                if fixed < 0:
                    raise ConfigurationError("Fixed payouts cannot be negative.")
                guaranteed[ticket.id] = fixed
            elif ratio is not None:
                guaranteed[ticket.id] = ratio.apply(ticket.purchase_price)
        accumulated_jackpot = max(jackpot_balance - base_jackpot, 0)
        for match_code, share in self.tier_pool_payouts.items():
            winners = [ticket for ticket in tickets if matches[ticket.id] == match_code]
            for ticket_id, amount in _allocate_evenly(
                share.apply(accumulated_jackpot), winners
            ).items():
                guaranteed[ticket_id] = guaranteed.get(ticket_id, 0) + amount
        guaranteed_total = sum(guaranteed.values())
        jackpot_tickets = [
            ticket for ticket in tickets if matches[ticket.id] == self.jackpot_match
        ]
        jackpot_reset_credit = base_jackpot if jackpot_tickets else 0
        fund_used = guaranteed_total + jackpot_reset_credit
        if fund_used > reserve_balance:
            raise InsufficientReserve(
                "Kasper Fund cannot cover all ordinary payouts and jackpot resets."
            )
        jackpot_payouts = _allocate_evenly(jackpot_balance, jackpot_tickets)
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
        return SettlementPlan(
            winning,
            payouts,
            0,
            0,
            fund_used,
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
    PayoutRatio(1),
    MappingProxyType({2: PayoutRatio(1, 4), 3: PayoutRatio(1)}),
    None,
    5,
    MappingProxyType({4: 50_000}),
    True,
)
KASPER_GRAND_RULES = LotteryRuleStrategy(
    code="weekly_grand_5_35_2_5",
    label="Kasper Grand",
    numbers_to_pick=7,
    max_number=40,
    price_divisor=1,
    jackpot_share=PayoutRatio(1),
    guaranteed_payouts=MappingProxyType({}),
    distribution_pool_match=None,
    jackpot_match=52,
    jackpot_refill_from_reserve=True,
    primary_numbers_to_pick=5,
    primary_max_number=35,
    secondary_numbers_to_pick=2,
    secondary_max_number=5,
    secondary_storage_offset=35,
    tier_pool_payouts=MappingProxyType(
        {
            51: PayoutRatio(20, 100),
            50: PayoutRatio(10, 100),
            42: PayoutRatio(8, 100),
            41: PayoutRatio(4, 100),
            32: PayoutRatio(2, 100),
        }
    ),
)
DAILY_RULES = LotteryRuleStrategy(
    "daily_4_15",
    "Daily",
    4,
    15,
    2,
    PayoutRatio(1),
    MappingProxyType({2: PayoutRatio(1, 2), 3: PayoutRatio(3)}),
    None,
    4,
    jackpot_refill_from_reserve=True,
)
CLASSIC_6_36_RULES = LotteryRuleStrategy(
    "classic_6_36",
    "6 из 36",
    6,
    36,
    2,
    PayoutRatio(1),
    MappingProxyType(
        {
            2: PayoutRatio(1, 4),
            3: PayoutRatio(1),
            4: PayoutRatio(10),
            5: PayoutRatio(100),
        }
    ),
    None,
    6,
    jackpot_refill_from_reserve=True,
)
SEPTEMBER_RULES = LotteryRuleStrategy(
    "september_3_33",
    "3 СЕНТЯБРЯ",
    3,
    33,
    1,
    PayoutRatio(1),
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
    PayoutRatio(1),
    MappingProxyType({}),
    None,
    3,
    MappingProxyType({1: 666, 2: 6_666}),
    True,
)
FAST_RULES = LotteryRuleStrategy(
    "fast_3_15",
    "Fast",
    3,
    15,
    1,
    PayoutRatio(1),
    MappingProxyType({}),
    None,
    3,
    MappingProxyType({1: 88, 2: 888}),
    True,
)
PULSE_RULES = LotteryRuleStrategy(
    code="pulse_2_10_1_5",
    label="PULSE",
    numbers_to_pick=3,
    max_number=15,
    price_divisor=1,
    jackpot_share=PayoutRatio(1),
    guaranteed_payouts=MappingProxyType({}),
    distribution_pool_match=None,
    jackpot_match=21,
    fixed_payouts=MappingProxyType({1: 88, 10: 88, 11: 888, 20: 888}),
    jackpot_refill_from_reserve=True,
    primary_numbers_to_pick=2,
    primary_max_number=10,
    secondary_numbers_to_pick=1,
    secondary_max_number=5,
    secondary_storage_offset=10,
)
BINGO_RULES = LotteryRuleStrategy(
    "bingo_12_60",
    "Kasper Bingo",
    12,
    60,
    1,
    PayoutRatio(1),
    MappingProxyType({}),
    None,
    12,
    jackpot_refill_from_reserve=True,
)
LOTTERY_RULES: Mapping[str, LotteryRuleStrategy] = MappingProxyType(
    {
        rule.code: rule
        for rule in (
            BINGO_RULES,
            WEEKLY_RULES,
            KASPER_GRAND_RULES,
            DAILY_RULES,
            CLASSIC_6_36_RULES,
            SEPTEMBER_RULES,
            GROB_RULES,
            FAST_RULES,
            PULSE_RULES,
        )
    }
)


def get_lottery_rules(code: str) -> LotteryRuleStrategy:
    try:
        return LOTTERY_RULES[code]
    except KeyError as error:
        raise ConfigurationError(f"Unknown lottery rule strategy: {code!r}.") from error
