"""Comprehensive tests for Weekly 5/20 business mathematics."""

from uuid import UUID

import pytest

from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InsufficientReserve,
    InvalidTicket,
)
from k_loto.domain.weekly import (
    SettlementTicket,
    SystemRandomNumberGenerator,
    calculate_weekly_settlement,
    quote_weekly_purchase,
    validate_weekly_combination,
)

WINNING = (1, 2, 3, 4, 5)


def ticket(
    public_number: int,
    numbers: tuple[int, ...],
    *,
    price: int = 100,
    user_number: int = 1,
) -> SettlementTicket:
    return SettlementTicket(
        id=UUID(int=public_number),
        public_number=public_number,
        user_id=UUID(int=10_000 + user_number),
        numbers=numbers,
        purchase_price=price,
    )


def settle(
    tickets: list[SettlementTicket],
    *,
    distribution: int = 1_000,
    jackpot: int = 10_000,
    reserve: int = 1_000_000_000,
    base_jackpot: int = 2_000,
):
    return calculate_weekly_settlement(
        tickets,
        WINNING,
        distribution_balance=distribution,
        jackpot_balance=jackpot,
        reserve_balance=reserve,
        base_jackpot=base_jackpot,
    )


def test_valid_ticket_is_canonicalized() -> None:
    assert validate_weekly_combination([5, 1, 4, 2, 3]) == WINNING


@pytest.mark.parametrize(
    "numbers",
    [
        [1, 2, 3, 4],
        [1, 2, 3, 4, 5, 6],
        [1, 1, 2, 3, 4],
        [0, 1, 2, 3, 4],
        [1, 2, 3, 4, 21],
        [True, 2, 3, 4, 5],
    ],
)
def test_invalid_ticket_is_rejected(numbers: list[int]) -> None:
    with pytest.raises(InvalidTicket):
        validate_weekly_combination(numbers)


def test_multi_ticket_purchase_and_identical_combinations() -> None:
    quote = quote_weekly_purchase([list(WINNING), list(WINNING)], 100, 500)

    assert len(quote.combinations) == 2
    assert quote.combinations[0] == quote.combinations[1]
    assert quote.total_cost == 200
    assert quote.jackpot_contribution == 200
    assert quote.distribution_contribution == 0


def test_purchase_rejects_insufficient_balance() -> None:
    with pytest.raises(InsufficientBalance):
        quote_weekly_purchase([list(WINNING), list(WINNING)], 100, 199)


def test_weekly_price_must_support_exact_quarter_payout() -> None:
    with pytest.raises(ConfigurationError):
        quote_weekly_purchase([list(WINNING)], 99, 1_000)


@pytest.mark.parametrize(
    ("numbers", "matches"),
    [
        ((6, 7, 8, 9, 10), 0),
        ((1, 6, 7, 8, 9), 1),
    ],
)
def test_zero_and_one_match_pay_zero(numbers: tuple[int, ...], matches: int) -> None:
    plan = settle([ticket(1, numbers)])

    assert plan.payouts[0].matches == matches
    assert plan.payouts[0].amount == 0
    assert plan.distribution_closing == 0
    assert plan.jackpot_closing == 10_000


def test_two_matches_pay_quarter_of_ticket_snapshot() -> None:
    plan = settle([ticket(1, (1, 2, 6, 7, 8), price=200)])

    assert plan.payouts[0].amount == 50
    assert plan.reserve_used == 50


def test_three_matches_refund_ticket_snapshot() -> None:
    plan = settle([ticket(1, (1, 2, 3, 6, 7), price=200)])

    assert plan.payouts[0].amount == 200
    assert plan.reserve_used == 200


def test_four_matches_pay_fixed_fifty_thousand_from_kasper_fund() -> None:
    tickets = [
        ticket(1, (1, 2, 6, 7, 8)),
        ticket(2, (1, 2, 3, 6, 7)),
        ticket(3, (1, 2, 3, 4, 6)),
    ]
    plan = settle(tickets)

    assert [item.amount for item in plan.payouts] == [25, 100, 50_000]
    assert plan.distribution_closing == 0
    assert plan.total_payout == 50_125
    assert plan.reserve_used == 50_125


def test_multiple_four_match_winners_each_receive_fixed_prize() -> None:
    plan = settle(
        [
            ticket(20, (1, 2, 3, 4, 6)),
            ticket(10, (1, 2, 3, 4, 7)),
        ],
        distribution=1_001,
    )

    payouts = {item.public_number: item.amount for item in plan.payouts}
    assert payouts == {10: 50_000, 20: 50_000}
    assert plan.distribution_closing == 0


def test_single_five_match_ticket_wins_jackpot_and_resets_it() -> None:
    plan = settle([ticket(1, WINNING)], jackpot=12_345, base_jackpot=2_000)

    assert plan.payouts[0].amount == 12_345
    assert plan.jackpot_won
    assert plan.jackpot_reset_credit == 2_000
    assert plan.jackpot_closing == 2_000


def test_multiple_jackpot_winners_are_individual_tickets() -> None:
    plan = settle(
        [ticket(2, WINNING, user_number=1), ticket(1, WINNING, user_number=1)],
        jackpot=1_001,
    )

    payouts = {item.public_number: item.amount for item in plan.payouts}
    assert payouts == {1: 501, 2: 500}
    assert plan.total_payout == 1_001


def test_jackpot_carries_when_no_five_match_ticket_exists() -> None:
    plan = settle([ticket(1, (1, 2, 3, 4, 6))], jackpot=12_345)

    assert not plan.jackpot_won
    assert plan.jackpot_closing == 12_345
    assert plan.jackpot_reset_credit == 0


def test_legacy_distribution_is_not_used_by_new_settlement() -> None:
    plan = settle([ticket(1, (6, 7, 8, 9, 10))], distribution=777)

    assert plan.distribution_closing == 0


def test_kasper_fund_covers_ordinary_payout() -> None:
    plan = settle(
        [ticket(1, (1, 2, 3, 6, 7))],
        distribution=40,
        reserve=100,
    )

    assert plan.payouts[0].amount == 100
    assert plan.distribution_closing == 0
    assert plan.reserve_used == 100


def test_insufficient_kasper_fund_aborts_the_plan() -> None:
    with pytest.raises(InsufficientReserve):
        settle(
            [ticket(1, (1, 2, 3, 6, 7))],
            distribution=40,
            reserve=99,
        )


def test_empty_draw_is_completed_mathematically_with_carryovers() -> None:
    plan = settle([], distribution=777, jackpot=12_345)

    assert plan.payouts == ()
    assert plan.total_payout == 0
    assert plan.distribution_closing == 0
    assert plan.jackpot_closing == 12_345


def test_official_rng_always_returns_five_unique_sorted_numbers() -> None:
    generator = SystemRandomNumberGenerator()

    for _ in range(100):
        result = generator.draw(20, 5)
        assert len(result) == 5
        assert len(set(result)) == 5
        assert result == tuple(sorted(result))
        assert all(1 <= number <= 20 for number in result)


def test_same_settlement_input_is_deterministic() -> None:
    tickets = [ticket(1, (1, 2, 3, 4, 6)), ticket(2, (1, 2, 3, 4, 7))]

    assert settle(tickets, distribution=1_001) == settle(tickets, distribution=1_001)
