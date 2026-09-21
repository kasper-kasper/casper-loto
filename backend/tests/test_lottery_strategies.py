"""Universal rule and interval schedule regression tests."""

from datetime import UTC, datetime
from math import comb
from types import MappingProxyType
from uuid import UUID
from zoneinfo import ZoneInfo

from k_loto.domain.enums import LotteryKind
from k_loto.domain.lottery_rules import (
    CLASSIC_6_36_RULES,
    CODE_RULES,
    FAST_RULES,
    GROB_RULES,
    LEGACY_CODE_RULES,
    LEGACY_FAST_RULES,
    LEGACY_FLASH_RULES,
    LEGACY_FLASH_V2_RULES,
    LEGACY_PULSE_RULES,
    LEGACY_PULSE_V2_RULES,
    LEGACY_PULSE_V3_RULES,
    PULSE_RULES,
    SEPTEMBER_RULES,
    LotteryRuleStrategy,
    PayoutRatio,
    SettlementTicket,
    get_lottery_rules,
)
from k_loto.domain.schedules import future_draw_target, next_draw_at


def test_new_three_of_thirty_three_format_needs_no_new_service_math() -> None:
    rules = LotteryRuleStrategy(
        code="daily_3_33",
        label="Example",
        numbers_to_pick=3,
        max_number=33,
        price_divisor=10,
        jackpot_share=PayoutRatio(3, 10),
        guaranteed_payouts=MappingProxyType({2: PayoutRatio(2)}),
        distribution_pool_match=None,
        jackpot_match=3,
    )
    quote = rules.quote_purchase([[3, 2, 1]], 100, 1_000)
    assert quote.jackpot_contribution == 30
    assert quote.distribution_contribution == 70
    plan = rules.calculate_settlement(
        [SettlementTicket(UUID(int=1), 1, UUID(int=2), (1, 2, 9), 100)],
        (1, 2, 3),
        distribution_balance=50,
        jackpot_balance=1_000,
        reserve_balance=1_000,
        base_jackpot=500,
    )
    assert plan.payouts[0].amount == 200
    assert plan.reserve_used == 200
    assert plan.jackpot_closing == 1_000


def test_classic_six_of_thirty_six_uses_classic_prize_ladder() -> None:
    assert CLASSIC_6_36_RULES.validate_combination([1, 8, 17, 23, 31, 36]) == (
        1,
        8,
        17,
        23,
        31,
        36,
    )
    tickets = [
        SettlementTicket(
            UUID(int=101), 1, UUID(int=201), (1, 2, 9, 10, 11, 12), 48_000
        ),
        SettlementTicket(
            UUID(int=102), 2, UUID(int=202), (1, 2, 3, 10, 11, 12), 48_000
        ),
        SettlementTicket(UUID(int=103), 3, UUID(int=203), (1, 2, 3, 4, 11, 12), 48_000),
        SettlementTicket(UUID(int=104), 4, UUID(int=204), (1, 2, 3, 4, 5, 12), 48_000),
        SettlementTicket(UUID(int=105), 5, UUID(int=205), (1, 2, 3, 4, 5, 6), 48_000),
    ]
    plan = CLASSIC_6_36_RULES.calculate_settlement(
        tickets,
        (1, 2, 3, 4, 5, 6),
        distribution_balance=0,
        jackpot_balance=33_456_000,
        reserve_balance=40_000_000,
        base_jackpot=30_000_000,
    )

    assert [item.matches for item in plan.payouts] == [2, 3, 4, 5, 6]
    assert [item.amount for item in plan.payouts] == [
        12_000,
        48_000,
        480_000,
        4_800_000,
        33_456_000,
    ]
    assert plan.jackpot_closing == 30_000_000


def test_interval_schedule_is_server_anchored_in_moscow() -> None:
    moscow = ZoneInfo("Europe/Moscow")
    result = next_draw_at(
        LotteryKind.DAILY,
        datetime(2026, 9, 1, 12, 1, tzinfo=moscow),
        {"type": "interval", "interval_minutes": 30, "anchor_time": "00:00"},
    )
    assert result == datetime(2026, 9, 1, 9, 30, tzinfo=UTC)
    assert (
        future_draw_target(
            LotteryKind.DAILY, {"type": "interval", "interval_minutes": 30}
        )
        == 2
    )


def test_flash_five_of_twenty_only_pays_the_jackpot() -> None:
    quote = FAST_RULES.quote_purchase(
        [[1, 2, 3, 4, 5], [16, 17, 18, 19, 20]], 888, 10_000
    )
    assert quote.total_cost == 1_776
    assert quote.jackpot_contribution == 1_776
    assert quote.distribution_contribution == 0

    tickets = [
        SettlementTicket(UUID(int=61), 1, UUID(int=71), (1, 2, 3, 4, 9), 888),
        SettlementTicket(UUID(int=62), 2, UUID(int=72), (1, 2, 3, 4, 5), 888),
    ]
    plan = FAST_RULES.calculate_settlement(
        tickets,
        (1, 2, 3, 4, 5),
        distribution_balance=0,
        jackpot_balance=888_889,
        reserve_balance=2_000_000,
        base_jackpot=888_888,
    )
    assert [item.amount for item in plan.payouts] == [0, 888_889]
    assert plan.jackpot_closing == 888_888
    assert plan.reserve_used == 888_888


def test_code_preserves_order_allows_zero_and_repeated_digits() -> None:
    assert CODE_RULES.validate_combination([0, 7, 0, 3, 9]) == (0, 7, 0, 3, 9)

    quote = CODE_RULES.quote_purchase([[0, 7, 0, 3, 9]], 999, 1_000)
    assert quote.jackpot_contribution == 999
    assert quote.distribution_contribution == 0


def test_code_pays_four_positions_and_jackpot_for_all_five() -> None:
    tickets = [
        SettlementTicket(UUID(int=111), 1, UUID(int=121), (0, 7, 0, 3, 8), 999),
        SettlementTicket(UUID(int=112), 2, UUID(int=122), (0, 7, 0, 3, 9), 999),
    ]
    plan = CODE_RULES.calculate_settlement(
        tickets,
        (0, 7, 0, 3, 9),
        distribution_balance=0,
        jackpot_balance=1_239_760,
        reserve_balance=3_000_000,
        base_jackpot=1_000_000,
    )

    assert [item.matches for item in plan.payouts] == [4, 5]
    assert [item.amount for item in plan.payouts] == [1_500_000, 1_239_760]
    assert plan.jackpot_closing == 1_000_000
    assert plan.reserve_used == 2_500_000


def test_code_generator_uses_five_independent_digit_positions() -> None:
    class Generator:
        def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]:
            raise AssertionError("CODE must not use a unique-number draw")

        def draw_sequence(
            self, minimum: int, maximum: int, length: int
        ) -> tuple[int, ...]:
            assert (minimum, maximum, length) == (0, 9, 5)
            return (4, 4, 0, 9, 2)

    assert CODE_RULES.generate_combination(Generator()) == (4, 4, 0, 9, 2)


def test_fast_schedules_rotate_every_three_minutes_without_collisions() -> None:
    moscow = ZoneInfo("Europe/Moscow")
    after = datetime(2026, 9, 1, 12, 1, tzinfo=moscow)
    flash = next_draw_at(
        LotteryKind.DAILY,
        after,
        {"type": "interval", "interval_minutes": 9, "anchor_time": "00:00"},
    )
    shadow = next_draw_at(
        LotteryKind.DAILY,
        after,
        {"type": "interval", "interval_minutes": 9, "anchor_time": "00:03"},
    )
    pulse = next_draw_at(
        LotteryKind.DAILY,
        after,
        {"type": "interval", "interval_minutes": 9, "anchor_time": "00:06"},
    )
    assert shadow == datetime(2026, 9, 1, 9, 3, tzinfo=UTC)
    assert pulse == datetime(2026, 9, 1, 9, 6, tzinfo=UTC)
    assert flash == datetime(2026, 9, 1, 9, 9, tzinfo=UTC)


def test_pulse_cipher_pays_numbers_only_or_the_jackpot() -> None:
    tickets = [
        SettlementTicket(UUID(int=81), 1, UUID(int=91), (1, 2, 14, 15, 1087), 1_234),
        SettlementTicket(UUID(int=82), 2, UUID(int=92), (1, 2, 14, 15, 1042), 1_234),
        SettlementTicket(UUID(int=83), 3, UUID(int=93), (1, 8, 14, 15, 1042), 1_234),
    ]
    plan = PULSE_RULES.calculate_settlement(
        tickets,
        (1, 2, 14, 15, 1042),
        distribution_balance=0,
        jackpot_balance=1_235_000,
        reserve_balance=2_000_000,
        base_jackpot=1_234_567,
    )
    assert [item.matches for item in plan.payouts] == [220, 221, 121]
    assert [item.amount for item in plan.payouts] == [500_000, 1_235_000, 0]
    assert plan.jackpot_closing == 1_234_567
    assert plan.reserve_used == 1_734_567


def test_pulse_cipher_is_assigned_by_the_server() -> None:
    class Generator:
        def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]:
            assert (population_size, numbers_to_pick) == (199, 1)
            return (87,)

        def draw_sequence(
            self, minimum: int, maximum: int, length: int
        ) -> tuple[int, ...]:
            raise AssertionError("PULSE must not generate a sequence")

    assert PULSE_RULES.complete_purchase_combination([1, 12, 13, 18], Generator()) == (
        1,
        12,
        13,
        18,
        1087,
    )


def test_existing_fast_draws_keep_their_legacy_rules() -> None:
    assert get_lottery_rules("fast_3_15") is LEGACY_FAST_RULES
    assert get_lottery_rules("fast_3_16") is LEGACY_FLASH_RULES
    assert get_lottery_rules("fast_3_20") is LEGACY_FLASH_V2_RULES
    assert get_lottery_rules("pulse_2_10_1_5") is LEGACY_PULSE_RULES
    assert get_lottery_rules("pulse_2_10_2_5") is LEGACY_PULSE_V2_RULES
    assert get_lottery_rules("pulse_2_12_2_6") is LEGACY_PULSE_V3_RULES
    assert get_lottery_rules("code_4_digits") is LEGACY_CODE_RULES
    assert LEGACY_FAST_RULES.validate_combination([13, 14, 15]) == (13, 14, 15)
    assert LEGACY_FLASH_RULES.validate_combination([14, 15, 16]) == (14, 15, 16)
    assert LEGACY_PULSE_RULES.validate_combination([1, 10, 15]) == (1, 10, 15)
    assert LEGACY_PULSE_V2_RULES.validate_combination([1, 10, 11, 15]) == (
        1,
        10,
        11,
        15,
    )


def test_rebalanced_fast_jackpot_odds() -> None:
    assert comb(FAST_RULES.max_number, FAST_RULES.numbers_to_pick) == 15_504
    assert (
        comb(PULSE_RULES.primary_max_number, PULSE_RULES.primary_numbers_to_pick)
        * comb(
            PULSE_RULES.secondary_max_number,
            PULSE_RULES.secondary_numbers_to_pick,
        )
        * PULSE_RULES.server_code_max
        == 197_010
    )


def test_september_fixed_payouts_and_shared_main_prize() -> None:
    tickets = [
        SettlementTicket(UUID(int=1), 10, UUID(int=11), (1, 8, 9), 333),
        SettlementTicket(UUID(int=2), 11, UUID(int=12), (1, 2, 9), 333),
        SettlementTicket(UUID(int=3), 12, UUID(int=13), (1, 2, 3), 333),
        SettlementTicket(UUID(int=4), 13, UUID(int=14), (1, 2, 3), 333),
    ]
    plan = SEPTEMBER_RULES.calculate_settlement(
        tickets,
        (1, 2, 3),
        distribution_balance=1_000,
        jackpot_balance=33_333_333,
        reserve_balance=1_000_000_000,
        base_jackpot=33_333_333,
    )

    assert [item.matches for item in plan.payouts] == [1, 2, 3, 3]
    assert [item.amount for item in plan.payouts] == [
        333,
        3_333,
        16_666_667,
        16_666_666,
    ]
    assert plan.distribution_closing == 0
    assert plan.reserve_used == 33_336_999
    assert plan.jackpot_closing == 33_333_333
    assert plan.jackpot_reset_credit == 33_333_333


def test_september_purchase_goes_entirely_to_jackpot() -> None:
    quote = SEPTEMBER_RULES.quote_purchase([[33, 1, 3], [4, 5, 6]], 333, 1_000)
    assert quote.combinations == ((1, 3, 33), (4, 5, 6))
    assert quote.total_cost == 666
    assert quote.jackpot_contribution == 666
    assert quote.distribution_contribution == 0


def test_september_schedule_has_two_moscow_slots() -> None:
    moscow = ZoneInfo("Europe/Moscow")
    schedule = {"slots": ["03:33", "15:33"]}
    morning = next_draw_at(
        LotteryKind.DAILY,
        datetime(2026, 9, 1, 3, 0, tzinfo=moscow),
        schedule,
    )
    afternoon = next_draw_at(LotteryKind.DAILY, morning, schedule)
    assert morning == datetime(2026, 9, 1, 0, 33, tzinfo=UTC)
    assert afternoon == datetime(2026, 9, 1, 12, 33, tzinfo=UTC)
    assert future_draw_target(LotteryKind.DAILY, schedule) == 2


def test_grob_purchase_goes_entirely_to_jackpot_and_is_bulk_invariant() -> None:
    single = GROB_RULES.quote_purchase([[1, 2, 3]], 6_666, 100_000)
    bulk = GROB_RULES.quote_purchase(
        [[1, 2, 3], [4, 5, 6], [14, 15, 16]], 6_666, 100_000
    )

    assert (single.jackpot_contribution, single.distribution_contribution) == (6_666, 0)
    assert bulk.jackpot_contribution == single.jackpot_contribution * 3
    assert bulk.distribution_contribution == single.distribution_contribution * 3


def test_grob_fixed_prizes_use_kasper_fund() -> None:
    tickets = [
        SettlementTicket(UUID(int=21), 1, UUID(int=31), (1, 8, 9), 6_666),
        SettlementTicket(UUID(int=22), 2, UUID(int=32), (1, 2, 9), 6_666),
        SettlementTicket(UUID(int=23), 3, UUID(int=33), (8, 9, 10), 6_666),
    ]
    plan = GROB_RULES.calculate_settlement(
        tickets,
        (1, 2, 3),
        distribution_balance=5_000,
        jackpot_balance=6_666_666,
        reserve_balance=10_000,
        base_jackpot=6_666_666,
    )

    assert [item.matches for item in plan.payouts] == [1, 2, 0]
    assert [item.amount for item in plan.payouts] == [666, 6_666, 0]
    assert plan.distribution_closing == 0
    assert plan.reserve_used == 7_332
    assert plan.jackpot_closing == 6_666_666


def test_grob_jackpot_is_shared_and_resets_to_base() -> None:
    tickets = [
        SettlementTicket(UUID(int=41), 1, UUID(int=51), (1, 2, 3), 6_666),
        SettlementTicket(UUID(int=42), 2, UUID(int=52), (1, 2, 3), 6_666),
    ]
    plan = GROB_RULES.calculate_settlement(
        tickets,
        (1, 2, 3),
        distribution_balance=8_000,
        jackpot_balance=6_666_667,
        reserve_balance=1_000_000_000,
        base_jackpot=6_666_666,
    )

    assert [item.amount for item in plan.payouts] == [3_333_334, 3_333_333]
    assert plan.jackpot_closing == 6_666_666
    assert plan.jackpot_reset_credit == 6_666_666
    assert plan.distribution_closing == 0
    assert plan.reserve_used == 6_666_666


def test_grob_schedule_has_two_moscow_slots() -> None:
    moscow = ZoneInfo("Europe/Moscow")
    schedule = {"slots": ["06:06", "23:06"]}
    morning = next_draw_at(
        LotteryKind.DAILY,
        datetime(2026, 9, 1, 6, 0, tzinfo=moscow),
        schedule,
    )
    evening = next_draw_at(LotteryKind.DAILY, morning, schedule)

    assert morning == datetime(2026, 9, 1, 3, 6, tzinfo=UTC)
    assert evening == datetime(2026, 9, 1, 20, 6, tzinfo=UTC)
    assert future_draw_target(LotteryKind.DAILY, schedule) == 2
