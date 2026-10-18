"""Declarative, reusable lottery purchase and payout strategies."""

import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from k_loto.domain.dual import DUAL_ECONOMY_PAYOUTS
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
    jackpot_distributed: bool = False
    distribution_category: str | None = None

    @property
    def jackpot_won(self) -> bool:
        if self.jackpot_distributed:
            return False
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

    def draw_sequence(
        self, minimum: int, maximum: int, length: int
    ) -> tuple[int, ...]: ...


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
    minimum_number: int = 1
    allow_repeats: bool = False
    ordered: bool = False
    server_code_max: int = 0
    server_code_storage_offset: int = 0

    @property
    def display_primary_numbers_to_pick(self) -> int:
        return self.primary_numbers_to_pick or self.numbers_to_pick

    @property
    def display_primary_max_number(self) -> int:
        return self.primary_max_number or self.max_number

    def validate_combination(
        self, numbers: tuple[int, ...] | list[int]
    ) -> tuple[int, ...]:
        if self.code in ("bingo_12_60", "bingo_12_60_economy_v2"):
            from k_loto.domain.bingo import validate_ticket

            return validate_ticket(numbers)
        if len(numbers) != self.numbers_to_pick:
            raise InvalidTicket(
                f"{self.label} tickets require exactly {self.numbers_to_pick} numbers."
            )
        if any(
            isinstance(value, bool) or not isinstance(value, int) for value in numbers
        ):
            raise InvalidTicket("Ticket numbers must be integers.")
        if not self.allow_repeats and len(set(numbers)) != self.numbers_to_pick:
            raise InvalidTicket("Ticket numbers must be unique.")
        ordinary_numbers = (
            [value for value in numbers if value <= self.server_code_storage_offset]
            if self.server_code_max
            else list(numbers)
        )
        if any(
            value < self.minimum_number or value > self.max_number
            for value in ordinary_numbers
        ):
            raise InvalidTicket(
                f"{self.label} ticket numbers must be between "
                f"{self.minimum_number} and {self.max_number}."
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
            codes = [
                value
                for value in numbers
                if self.server_code_storage_offset
                < value
                <= self.server_code_storage_offset + self.server_code_max
            ]
            if (
                len(primary) != self.display_primary_numbers_to_pick
                or len(secondary) != self.secondary_numbers_to_pick
                or len(codes) != (1 if self.server_code_max else 0)
                or len(primary) + len(secondary) + len(codes) != len(numbers)
            ):
                raise InvalidTicket(
                    f"{self.label} tickets require "
                    f"{self.display_primary_numbers_to_pick} main and "
                    f"{self.secondary_numbers_to_pick} special numbers."
                )
        return tuple(numbers) if self.ordered else tuple(sorted(numbers))

    def validate_purchase_combination(
        self, numbers: tuple[int, ...] | list[int]
    ) -> tuple[int, ...]:
        """Validate the numbers chosen by a player before a server code is added."""
        if not self.server_code_max:
            return self.validate_combination(numbers)
        if len(numbers) != self.numbers_to_pick - 1:
            raise InvalidTicket(
                f"{self.label} tickets require exactly {self.numbers_to_pick - 1} "
                "player numbers."
            )
        placeholder = self.server_code_storage_offset + 1
        return self.validate_combination([*numbers, placeholder])[:-1]

    def complete_purchase_combination(
        self,
        numbers: tuple[int, ...] | list[int],
        generator: NumberGenerator,
    ) -> tuple[int, ...]:
        chosen = self.validate_purchase_combination(numbers)
        if not self.server_code_max:
            return chosen
        code = generator.draw(self.server_code_max, 1)[0]
        return self.validate_combination(
            [*chosen, self.server_code_storage_offset + code]
        )

    def generate_purchase_combination(
        self, generator: NumberGenerator
    ) -> tuple[int, ...]:
        generated = self.generate_combination(generator)
        return generated[:-1] if self.server_code_max else generated

    def generate_combination(self, generator: NumberGenerator) -> tuple[int, ...]:
        if self.code in ("bingo_12_60", "bingo_12_60_economy_v2"):
            from k_loto.domain.bingo import generate_ticket

            return generate_ticket()
        if self.ordered and self.allow_repeats:
            return generator.draw_sequence(
                self.minimum_number, self.max_number, self.numbers_to_pick
            )
        if not self.secondary_numbers_to_pick:
            return generator.draw(self.max_number, self.numbers_to_pick)
        primary = generator.draw(
            self.display_primary_max_number, self.display_primary_numbers_to_pick
        )
        secondary = generator.draw(
            self.secondary_max_number, self.secondary_numbers_to_pick
        )
        result = tuple(
            sorted(primary)
            + [self.secondary_storage_offset + value for value in sorted(secondary)]
        )
        if self.server_code_max:
            code = generator.draw(self.server_code_max, 1)[0]
            result += (self.server_code_storage_offset + code,)
        return result

    def match_count(
        self, ticket_numbers: tuple[int, ...], winning_numbers: tuple[int, ...]
    ) -> int:
        if self.ordered:
            return sum(
                ticket == winning
                for ticket, winning in zip(ticket_numbers, winning_numbers, strict=True)
            )
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
                if self.secondary_storage_offset
                < value
                <= self.secondary_storage_offset + self.secondary_max_number
            }.intersection(
                value
                for value in winning_numbers
                if self.secondary_storage_offset
                < value
                <= self.secondary_storage_offset + self.secondary_max_number
            )
        )
        if self.server_code_max:
            ticket_code = next(
                value
                for value in ticket_numbers
                if value > self.server_code_storage_offset
            )
            winning_code = next(
                value
                for value in winning_numbers
                if value > self.server_code_storage_offset
            )
            return (
                main_matches * 100
                + special_matches * 10
                + int(ticket_code == winning_code)
            )
        return main_matches * 10 + special_matches

    def jackpot_contribution(self, ticket_price: int) -> int:
        """Split one ticket; a half-CAS remainder belongs to the jackpot."""
        if self.jackpot_share.numerator * 2 == self.jackpot_share.denominator:
            return (ticket_price + 1) // 2
        return self.jackpot_share.apply(ticket_price)

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
        jackpot = self.jackpot_contribution(ticket_price) * len(canonical)
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
        if self.code in ("bingo_12_60", "bingo_12_60_economy_v2"):
            from k_loto.domain.bingo import BINGO_ECONOMY_CODE, outcomes

            results = outcomes(
                [(t.id, t.public_number, t.numbers) for t in tickets],
                tuple(winning_numbers),
                jackpot_balance,
                fixed_per_card=self.code == BINGO_ECONOMY_CODE,
            )
            won = any(r.amounts[2] > 0 for r in results.values())
            reset = base_jackpot if won else 0
            used = sum(sum(r.amounts) - r.amounts[2] for r in results.values()) + reset
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

    def draw_sequence(self, minimum: int, maximum: int, length: int) -> tuple[int, ...]:
        if length <= 0 or minimum > maximum:
            raise ValueError("Invalid draw sequence configuration.")
        return tuple(self._random.randint(minimum, maximum) for _ in range(length))


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
GRAND_FIXED_RULES = replace(
    KASPER_GRAND_RULES,
    code="grand_fixed_5_35_2_5",
    label="Casper Grand",
    fixed_payouts=MappingProxyType(
        {
            21: 50_000,
            22: 50_000,
            30: 100_000,
            31: 200_000,
            32: 300_000,
            40: 500_000,
            41: 1_000_000,
            42: 3_000_000,
            50: 10_000_000,
            51: 20_000_000,
        }
    ),
    tier_pool_payouts=MappingProxyType({}),
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
PSS_CASPER_BALL_RULES = LotteryRuleStrategy(
    code="casper_ball_5_36_1_8",
    label="Casper Ball",
    numbers_to_pick=6,
    max_number=44,
    price_divisor=2,
    jackpot_share=PayoutRatio(1),
    guaranteed_payouts=MappingProxyType({}),
    distribution_pool_match=None,
    jackpot_match=51,
    fixed_payouts=MappingProxyType(
        {
            50: 10_000_000,
            41: 1_000_000,
            40: 100_000,
            1: 12_000,
        }
    ),
    jackpot_refill_from_reserve=True,
    primary_numbers_to_pick=5,
    primary_max_number=36,
    secondary_numbers_to_pick=1,
    secondary_max_number=8,
    secondary_storage_offset=36,
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
DUAL_RULES = LotteryRuleStrategy(
    code="casper_dual_2_12_2_12",
    label="Casper Dual",
    numbers_to_pick=4,
    max_number=24,
    price_divisor=1,
    jackpot_share=PayoutRatio(0),
    guaranteed_payouts=MappingProxyType({}),
    distribution_pool_match=None,
    jackpot_match=22,
    primary_numbers_to_pick=2,
    primary_max_number=12,
    secondary_numbers_to_pick=2,
    secondary_max_number=12,
    secondary_storage_offset=12,
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
HALLOWEEN_RULES = LotteryRuleStrategy(
    "halloween_3_28",
    "Casper Halloween",
    3,
    28,
    1,
    PayoutRatio(1),
    MappingProxyType({}),
    None,
    3,
    MappingProxyType({2: 28_000}),
    True,
)
LEGACY_FAST_RULES = LotteryRuleStrategy(
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
LEGACY_FLASH_RULES = LotteryRuleStrategy(
    "fast_3_16",
    "FLASH",
    3,
    16,
    1,
    PayoutRatio(1),
    MappingProxyType({}),
    None,
    3,
    MappingProxyType({1: 88, 2: 888}),
    True,
)
LEGACY_FLASH_V2_RULES = LotteryRuleStrategy(
    "fast_3_20",
    "FLASH",
    3,
    20,
    1,
    PayoutRatio(1),
    MappingProxyType({}),
    None,
    3,
    MappingProxyType({1: 88, 2: 888}),
    True,
)
FAST_RULES = LotteryRuleStrategy(
    "fast_5_20_jackpot_only",
    "FLASH",
    5,
    20,
    1,
    PayoutRatio(1),
    MappingProxyType({}),
    None,
    5,
    jackpot_refill_from_reserve=True,
)
LEGACY_PULSE_RULES = LotteryRuleStrategy(
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
LEGACY_PULSE_V2_RULES = LotteryRuleStrategy(
    code="pulse_2_10_2_5",
    label="PULSE",
    numbers_to_pick=4,
    max_number=15,
    price_divisor=1,
    jackpot_share=PayoutRatio(1),
    guaranteed_payouts=MappingProxyType({}),
    distribution_pool_match=None,
    jackpot_match=22,
    fixed_payouts=MappingProxyType(
        {1: 88, 2: 888, 10: 88, 11: 888, 12: 888, 20: 888, 21: 888}
    ),
    jackpot_refill_from_reserve=True,
    primary_numbers_to_pick=2,
    primary_max_number=10,
    secondary_numbers_to_pick=2,
    secondary_max_number=5,
    secondary_storage_offset=10,
)
LEGACY_PULSE_V3_RULES = LotteryRuleStrategy(
    code="pulse_2_12_2_6",
    label="PULSE",
    numbers_to_pick=4,
    max_number=18,
    price_divisor=1,
    jackpot_share=PayoutRatio(1),
    guaranteed_payouts=MappingProxyType({}),
    distribution_pool_match=None,
    jackpot_match=22,
    fixed_payouts=MappingProxyType(
        {1: 88, 2: 888, 10: 88, 11: 888, 12: 888, 20: 888, 21: 888}
    ),
    jackpot_refill_from_reserve=True,
    primary_numbers_to_pick=2,
    primary_max_number=12,
    secondary_numbers_to_pick=2,
    secondary_max_number=6,
    secondary_storage_offset=12,
)
PULSE_RULES = LotteryRuleStrategy(
    code="pulse_2_12_2_6_cipher_199",
    label="PULSE",
    numbers_to_pick=5,
    max_number=18,
    price_divisor=1,
    jackpot_share=PayoutRatio(1),
    guaranteed_payouts=MappingProxyType({}),
    distribution_pool_match=None,
    jackpot_match=221,
    fixed_payouts=MappingProxyType({220: 500_000}),
    jackpot_refill_from_reserve=True,
    primary_numbers_to_pick=2,
    primary_max_number=12,
    secondary_numbers_to_pick=2,
    secondary_max_number=6,
    secondary_storage_offset=12,
    server_code_max=199,
    server_code_storage_offset=1_000,
)
LEGACY_CODE_RULES = LotteryRuleStrategy(
    code="code_4_digits",
    label="CODE",
    numbers_to_pick=4,
    max_number=9,
    price_divisor=1,
    jackpot_share=PayoutRatio(1),
    guaranteed_payouts=MappingProxyType({}),
    distribution_pool_match=None,
    jackpot_match=4,
    jackpot_refill_from_reserve=True,
    minimum_number=0,
    allow_repeats=True,
    ordered=True,
)
CODE_RULES = LotteryRuleStrategy(
    code="code_5_digits",
    label="CODE",
    numbers_to_pick=5,
    max_number=9,
    price_divisor=1,
    jackpot_share=PayoutRatio(1),
    guaranteed_payouts=MappingProxyType({}),
    distribution_pool_match=None,
    jackpot_match=5,
    fixed_payouts=MappingProxyType({4: 1_500_000}),
    jackpot_refill_from_reserve=True,
    minimum_number=0,
    allow_repeats=True,
    ordered=True,
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
BINGO_ECONOMY_RULES = replace(
    BINGO_RULES,
    code="bingo_12_60_economy_v2",
    jackpot_share=PayoutRatio(2, 5),
)
DUAL_ECONOMY_RULES = replace(
    DUAL_RULES,
    code="casper_dual_2_12_2_12_economy_v2",
    fixed_payouts=MappingProxyType(DUAL_ECONOMY_PAYOUTS),
)
# Persisted draws continue resolving their original immutable payout versions.
LEGACY_FLASH_V3_RULES = FAST_RULES
LEGACY_PULSE_V4_RULES = PULSE_RULES
LEGACY_CODE_V2_RULES = CODE_RULES
FAST_RULES = replace(
    FAST_RULES,
    code="fast_5_20_economy_v2",
    jackpot_share=PayoutRatio(2, 5),
    fixed_payouts=MappingProxyType({2: 2_000, 3: 8_000, 4: 100_000}),
)
CODE_RULES = replace(
    CODE_RULES,
    code="code_5_digits_economy_v2",
    jackpot_share=PayoutRatio(2, 5),
    fixed_payouts=MappingProxyType({1: 2_000, 2: 4_000, 3: 10_000, 4: 500_000}),
)
PULSE_RULES = replace(
    PULSE_RULES,
    code="pulse_2_12_2_6_cipher_199_economy_v2",
    jackpot_share=PayoutRatio(2, 5),
    fixed_payouts=MappingProxyType(
        {
            110: 4_000,
            111: 4_000,
            20: 4_000,
            21: 4_000,
            120: 8_000,
            121: 8_000,
            200: 14_000,
            201: 14_000,
            210: 14_000,
            211: 14_000,
            220: 500_000,
        }
    ),
)
CLASSIC_ECONOMY_RULES = replace(
    CLASSIC_6_36_RULES,
    code="classic_6_36_economy_v2",
    price_divisor=1,
    jackpot_share=PayoutRatio(2, 5),
    guaranteed_payouts=MappingProxyType({}),
    fixed_payouts=MappingProxyType({2: 30_000, 3: 140_000, 4: 1_000_000, 5: 7_000_000}),
)
BALL_ECONOMY_RULES = replace(
    PSS_CASPER_BALL_RULES,
    code="casper_ball_5_36_1_8_economy_v2",
    price_divisor=1,
    jackpot_share=PayoutRatio(2, 5),
    fixed_payouts=MappingProxyType(
        {
            1: 25_000,
            11: 100_000,
            20: 50_000,
            21: 100_000,
            30: 200_000,
            31: 400_000,
            40: 1_000_000,
            41: 5_000_000,
            50: 25_000_000,
        }
    ),
)
GRAND_ECONOMY_RULES = replace(
    GRAND_FIXED_RULES,
    code="grand_fixed_5_35_2_5_economy_v2",
    jackpot_share=PayoutRatio(2, 5),
    fixed_payouts=MappingProxyType(
        {
            20: 75_000,
            21: 150_000,
            22: 300_000,
            30: 650_000,
            31: 850_000,
            32: 1_200_000,
            40: 1_500_000,
            41: 3_000_000,
            42: 8_000_000,
            50: 30_000_000,
            51: 60_000_000,
        }
    ),
)
PLL_ECONOMY_RULES = replace(
    DAILY_RULES,
    code="pll_4_15_economy_v2",
    label="2:22",
    price_divisor=1,
    jackpot_share=PayoutRatio(1, 2),
    guaranteed_payouts=MappingProxyType({}),
    fixed_payouts=MappingProxyType({2: 22_222, 3: 44_444}),
)
HALLOWEEN_ECONOMY_RULES = replace(
    HALLOWEEN_RULES,
    code="halloween_3_28_economy_v2",
    jackpot_share=PayoutRatio(1, 2),
    fixed_payouts=MappingProxyType({2: 66_666}),
)
SEPTEMBER_ECONOMY_RULES = replace(
    SEPTEMBER_RULES,
    code="september_3_33_economy_v2",
    jackpot_share=PayoutRatio(1, 2),
    fixed_payouts=MappingProxyType({1: 3_333, 2: 9_999}),
)
LOTTERY_RULES: Mapping[str, LotteryRuleStrategy] = MappingProxyType(
    {
        rule.code: rule
        for rule in (
            BINGO_RULES,
            BINGO_ECONOMY_RULES,
            WEEKLY_RULES,
            KASPER_GRAND_RULES,
            GRAND_FIXED_RULES,
            GRAND_ECONOMY_RULES,
            DAILY_RULES,
            PLL_ECONOMY_RULES,
            PSS_CASPER_BALL_RULES,
            BALL_ECONOMY_RULES,
            CLASSIC_6_36_RULES,
            CLASSIC_ECONOMY_RULES,
            DUAL_RULES,
            DUAL_ECONOMY_RULES,
            SEPTEMBER_RULES,
            SEPTEMBER_ECONOMY_RULES,
            GROB_RULES,
            HALLOWEEN_RULES,
            HALLOWEEN_ECONOMY_RULES,
            LEGACY_FAST_RULES,
            LEGACY_FLASH_RULES,
            LEGACY_FLASH_V2_RULES,
            LEGACY_FLASH_V3_RULES,
            FAST_RULES,
            LEGACY_PULSE_RULES,
            LEGACY_PULSE_V2_RULES,
            LEGACY_PULSE_V3_RULES,
            LEGACY_PULSE_V4_RULES,
            PULSE_RULES,
            LEGACY_CODE_RULES,
            LEGACY_CODE_V2_RULES,
            CODE_RULES,
        )
    }
)


def get_lottery_rules(code: str) -> LotteryRuleStrategy:
    try:
        return LOTTERY_RULES[code]
    except KeyError as error:
        raise ConfigurationError(f"Unknown lottery rule strategy: {code!r}.") from error
