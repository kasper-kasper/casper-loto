from math import comb
from uuid import UUID

import pytest

from k_loto.domain.errors import InvalidTicket
from k_loto.domain.lottery_rules import KASPER_GRAND_RULES, SettlementTicket

WINNING = (1, 2, 3, 4, 5, 36, 37)


def ticket(public_number: int, numbers: tuple[int, ...]) -> SettlementTicket:
    return SettlementTicket(
        id=UUID(int=public_number),
        public_number=public_number,
        user_id=UUID(int=100 + public_number),
        numbers=numbers,
        purchase_price=5_000,
    )


def settle(tickets: list[SettlementTicket]):
    return KASPER_GRAND_RULES.calculate_settlement(
        tickets,
        WINNING,
        distribution_balance=0,
        jackpot_balance=6_000_000_000,
        reserve_balance=10_000_000_000,
        base_jackpot=5_000_000_000,
    )


def test_jackpot_probability_is_one_in_3_246_320() -> None:
    assert comb(35, 5) * comb(5, 2) == 3_246_320


def test_two_fields_are_validated_independently() -> None:
    assert KASPER_GRAND_RULES.validate_combination(WINNING) == WINNING
    with pytest.raises(InvalidTicket):
        KASPER_GRAND_RULES.validate_combination((1, 2, 3, 4, 5, 6, 36))
    with pytest.raises(InvalidTicket):
        KASPER_GRAND_RULES.validate_combination((1, 2, 3, 4, 36, 37, 38))


def test_rng_draws_the_main_and_special_fields_separately() -> None:
    class Generator:
        calls: list[tuple[int, int]] = []

        def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]:
            self.calls.append((population_size, numbers_to_pick))
            return (1, 2, 3, 4, 5) if population_size == 35 else (2, 5)

    generator = Generator()
    assert KASPER_GRAND_RULES.generate_combination(generator) == (
        1,
        2,
        3,
        4,
        5,
        37,
        40,
    )
    assert generator.calls == [(35, 5), (5, 2)]


def test_all_confirmed_tiers_use_only_the_accumulated_jackpot_as_basis() -> None:
    plan = settle(
        [
            ticket(1, (1, 2, 3, 4, 5, 36, 38)),  # 5+1
            ticket(2, (1, 2, 3, 4, 5, 38, 39)),  # 5+0
            ticket(3, (1, 2, 3, 4, 6, 36, 37)),  # 4+2
            ticket(4, (1, 2, 3, 4, 6, 36, 38)),  # 4+1
            ticket(5, (1, 2, 3, 6, 7, 36, 37)),  # 3+2
        ]
    )
    assert [(item.matches, item.amount) for item in plan.payouts] == [
        (51, 200_000_000),
        (50, 100_000_000),
        (42, 80_000_000),
        (41, 40_000_000),
        (32, 20_000_000),
    ]
    assert plan.reserve_used == 440_000_000
    assert plan.jackpot_closing == 6_000_000_000


def test_a_tier_pool_is_split_evenly_between_winning_tickets() -> None:
    plan = settle(
        [
            ticket(1, (1, 2, 3, 4, 5, 36, 38)),
            ticket(2, (1, 2, 3, 4, 5, 37, 39)),
        ]
    )
    assert [item.amount for item in plan.payouts] == [100_000_000, 100_000_000]


def test_five_plus_two_splits_the_full_jackpot_and_resets_it() -> None:
    plan = settle([ticket(1, WINNING), ticket(2, WINNING)])
    assert [item.amount for item in plan.payouts] == [3_000_000_000, 3_000_000_000]
    assert plan.jackpot_closing == 5_000_000_000
    assert plan.jackpot_reset_credit == 5_000_000_000
    assert plan.jackpot_won


def test_unclaimed_tier_shares_and_jackpot_carry_over() -> None:
    plan = settle([ticket(1, (6, 7, 8, 9, 10, 38, 39))])
    assert plan.total_payout == 0
    assert plan.reserve_used == 0
    assert plan.jackpot_closing == 6_000_000_000
