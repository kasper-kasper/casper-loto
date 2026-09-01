"""Universal rule and interval schedule regression tests."""

from datetime import UTC, datetime
from types import MappingProxyType
from uuid import UUID
from zoneinfo import ZoneInfo

from k_loto.domain.enums import LotteryKind
from k_loto.domain.lottery_rules import (
    LotteryRuleStrategy,
    PayoutRatio,
    SettlementTicket,
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
    assert plan.reserve_used == 150
    assert plan.jackpot_closing == 1_000


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
