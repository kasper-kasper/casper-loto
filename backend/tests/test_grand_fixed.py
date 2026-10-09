"""Approved fixed tiers and compensating Grand transition regressions."""

from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.lottery_transition import LotteryFormatTransitionService
from k_loto.domain.enums import TicketStatus
from k_loto.domain.errors import InsufficientReserve
from k_loto.domain.lottery_rules import (
    GRAND_FIXED_RULES,
    KASPER_GRAND_RULES,
    SettlementTicket,
)
from k_loto.infrastructure.database.models import LedgerTransaction
from test_halloween import NOW, objects
from test_weekly_application import FakeSession

WINNING = (1, 2, 3, 4, 5, 36, 37)


@pytest.mark.parametrize(
    "a,b,amount",
    [
        (2, 1, 50_000),
        (2, 2, 50_000),
        (3, 0, 100_000),
        (3, 1, 200_000),
        (3, 2, 300_000),
        (4, 0, 500_000),
        (4, 1, 1_000_000),
        (4, 2, 3_000_000),
        (5, 0, 10_000_000),
        (5, 1, 20_000_000),
        (1, 2, 0),
        (2, 0, 0),
        (0, 0, 0),
    ],
)
def test_exact_fixed_category_is_paid_per_ticket(a: int, b: int, amount: int) -> None:
    numbers = tuple(
        list(range(1, a + 1))
        + list(range(6, 6 + 5 - a))
        + list(range(36, 36 + b))
        + list(range(38, 38 + 2 - b))
    )
    tickets = [
        SettlementTicket(UUID(int=i), i, UUID(int=20 + i), numbers, 50_000)
        for i in (1, 2)
    ]
    plan = GRAND_FIXED_RULES.calculate_settlement(
        tickets,
        WINNING,
        distribution_balance=0,
        jackpot_balance=5_000_000_000,
        reserve_balance=50_000_000,
        base_jackpot=5_000_000_000,
    )
    assert [p.amount for p in plan.payouts] == [amount, amount]
    assert plan.reserve_used == amount * 2
    assert plan.jackpot_closing == 5_000_000_000


def test_jackpot_split_reset_and_fund_coverage() -> None:
    tickets = [
        SettlementTicket(UUID(int=i), i, UUID(int=20 + i), WINNING, 50_000)
        for i in (1, 2)
    ]
    args = dict(
        distribution_balance=0,
        jackpot_balance=5_000_000_001,
        reserve_balance=5_000_000_000,
        base_jackpot=5_000_000_000,
    )
    plan = GRAND_FIXED_RULES.calculate_settlement(tickets, WINNING, **args)
    assert [p.amount for p in plan.payouts] == [2_500_000_001, 2_500_000_000]
    assert plan.reserve_used == 5_000_000_000
    args["reserve_balance"] = 1
    with pytest.raises(InsufficientReserve):
        GRAND_FIXED_RULES.calculate_settlement(tickets, WINNING, **args)


async def test_grand_transition_returns_original_price_and_preserves_old_rule() -> None:
    owner, lottery, draw, ticket, jackpot, balance = objects()
    lottery.code = "weekly"
    lottery.ruleset_code = KASPER_GRAND_RULES.code
    lottery.numbers_to_pick = 7
    lottery.max_number = 40
    draw.configuration_snapshot = {
        "ruleset_code": KASPER_GRAND_RULES.code,
        "ticket_price": 6666,
    }
    ticket.numbers = list(WINNING)
    session = FakeSession(
        scalar_values=[owner, lottery, jackpot],
        scalar_collections=[[draw], [ticket], [balance]],
    )
    result = await LotteryFormatTransitionService(
        cast(AsyncSession, session),
        lottery_code="weekly",
        source_rules=KASPER_GRAND_RULES,
        target_rules=GRAND_FIXED_RULES,
        ticket_price=50_000,
        namespace="grand-fixed-v1",
    ).activate(owner_id=owner.id, now=NOW)
    assert result.refunded_cas == 6666
    assert ticket.status == TicketStatus.REFUNDED and ticket.numbers == list(WINNING)
    assert (
        lottery.ticket_price == 50_000
        and lottery.ruleset_code == GRAND_FIXED_RULES.code
    )
    assert draw.configuration_snapshot["ruleset_code"] == GRAND_FIXED_RULES.code
    entries = [item for item in session.added if isinstance(item, LedgerTransaction)]
    assert len(entries) == 2 and sum(item.amount for item in entries) == 0
    assert KASPER_GRAND_RULES.tier_pool_payouts and not KASPER_GRAND_RULES.fixed_payouts
