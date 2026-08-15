"""Comprehensive Daily 4/15 business mathematics tests."""

from uuid import UUID

import pytest

from k_loto.domain.daily import (
    calculate_daily_settlement,
    quote_daily_purchase,
    validate_daily_combination,
)
from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InsufficientReserve,
    InvalidTicket,
)
from k_loto.domain.weekly import SettlementTicket, SystemRandomNumberGenerator

WINNING = (1, 2, 3, 4)


def ticket(
    public_number: int,
    numbers: tuple[int, ...],
    *,
    price: int = 100,
    user_number: int = 1,
) -> SettlementTicket:
    return SettlementTicket(
        UUID(int=public_number),
        public_number,
        UUID(int=10_000 + user_number),
        numbers,
        price,
    )


def settle(
    tickets: list[SettlementTicket],
    *,
    distribution: int = 1_000,
    jackpot: int = 10_000,
    reserve: int = 5_000,
    base_jackpot: int = 2_000,
):
    return calculate_daily_settlement(
        tickets,
        WINNING,
        distribution_balance=distribution,
        jackpot_balance=jackpot,
        reserve_balance=reserve,
        base_jackpot=base_jackpot,
    )


def test_valid_daily_ticket_is_canonicalized() -> None:
    assert validate_daily_combination([4, 1, 3, 2]) == WINNING


@pytest.mark.parametrize(
    "numbers",
    (
        [1, 2, 3],
        [1, 2, 3, 4, 5],
        [1, 1, 2, 3],
        [0, 1, 2, 3],
        [1, 2, 3, 16],
        [True, 2, 3, 4],
    ),
)
def test_invalid_daily_ticket_is_rejected(numbers: list[int]) -> None:
    with pytest.raises(InvalidTicket):
        validate_daily_combination(numbers)


def test_purchase_split_is_40_percent_jackpot_and_60_distribution() -> None:
    quote = quote_daily_purchase([list(WINNING), list(WINNING)], 100, 500)

    assert quote.combinations == (WINNING, WINNING)
    assert quote.total_cost == 200
    assert quote.jackpot_contribution == 80
    assert quote.distribution_contribution == 120


def test_daily_price_must_support_all_exact_integer_rules() -> None:
    with pytest.raises(ConfigurationError):
        quote_daily_purchase([list(WINNING)], 45, 500)
    with pytest.raises(InsufficientBalance):
        quote_daily_purchase([list(WINNING)], 100, 99)


@pytest.mark.parametrize(
    ("numbers", "matches"),
    [((5, 6, 7, 8), 0), ((1, 5, 6, 7), 1)],
)
def test_zero_and_one_match_pay_zero(numbers: tuple[int, ...], matches: int) -> None:
    plan = settle([ticket(1, numbers)])

    assert plan.payouts[0].matches == matches
    assert plan.payouts[0].amount == 0
    assert plan.distribution_closing == 1_000
    assert plan.jackpot_closing == 10_000


def test_two_matches_pay_half_ticket_price() -> None:
    plan = settle([ticket(1, (1, 2, 5, 6), price=200)])

    assert plan.payouts[0].amount == 100
    assert plan.distribution_closing == 900


def test_three_matches_pay_three_times_ticket_price() -> None:
    plan = settle([ticket(1, (1, 2, 3, 5), price=200)])

    assert plan.payouts[0].amount == 600
    assert plan.distribution_closing == 400


def test_distribution_shortfall_uses_reserve_without_touching_jackpot() -> None:
    plan = settle(
        [ticket(1, (1, 2, 3, 5))], distribution=100, reserve=200, jackpot=12_345
    )

    assert plan.payouts[0].amount == 300
    assert plan.distribution_closing == 0
    assert plan.reserve_used == 200
    assert plan.jackpot_closing == 12_345


def test_insufficient_reserve_aborts_atomically() -> None:
    with pytest.raises(InsufficientReserve):
        settle([ticket(1, (1, 2, 3, 5))], distribution=100, reserve=199)


def test_jackpot_is_shared_with_deterministic_remainder_and_reset() -> None:
    plan = settle(
        [ticket(20, WINNING), ticket(10, WINNING)],
        jackpot=1_001,
        base_jackpot=2_000,
    )

    assert {item.public_number: item.amount for item in plan.payouts} == {
        10: 501,
        20: 500,
    }
    assert plan.jackpot_won
    assert plan.jackpot_closing == 2_000
    assert plan.jackpot_reset_credit == 2_000


def test_unwon_jackpot_and_unused_distribution_carry_over() -> None:
    plan = settle([ticket(1, (5, 6, 7, 8))], distribution=777, jackpot=12_345)

    assert plan.distribution_closing == 777
    assert plan.jackpot_closing == 12_345
    assert not plan.jackpot_won


def test_empty_daily_draw_completes_with_carryovers() -> None:
    plan = settle([], distribution=777, jackpot=12_345)

    assert plan.payouts == ()
    assert plan.total_payout == 0
    assert plan.distribution_closing == 777
    assert plan.jackpot_closing == 12_345


def test_secure_rng_supports_daily_4_of_15() -> None:
    generator = SystemRandomNumberGenerator()
    for _ in range(100):
        result = generator.draw(15, 4)
        assert len(result) == len(set(result)) == 4
        assert result == tuple(sorted(result))
        assert all(1 <= value <= 15 for value in result)
