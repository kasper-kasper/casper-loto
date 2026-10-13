"""Bingo payout boundaries and recovery, without probabilistic assertions."""

from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.weekly import (
    LotterySettlementService,
    LotteryTicketPurchaseService,
)
from k_loto.domain.bingo import closing_moves, generate_sequence, outcomes
from k_loto.domain.enums import DrawStatus, LotteryKind
from k_loto.domain.errors import InsufficientReserve
from k_loto.domain.lottery_rules import BINGO_RULES, SettlementTicket
from k_loto.infrastructure.database.models import (
    Balance,
    BingoPoolTicket,
    Draw,
    JackpotAccount,
    KasperFundAccount,
    Lottery,
    Ticket,
)
from test_weekly_application import FakeSession


@pytest.mark.parametrize("last,won", [(28, True), (29, False)])
def test_jackpot_includes_move_28_but_not_29(last: int, won: bool) -> None:
    tid = UUID(int=1)
    numbers = (*range(1, 12), last)
    result = outcomes([(tid, 1, numbers)], tuple(range(1, 59)), 10_000_000_000)[tid]
    assert result.amounts == (100_000, 500_000, 10_000_000_000 if won else 0)


def test_two_unrevealed_numbers_can_prevent_second_tour() -> None:
    tid = UUID(int=1)
    numbers = (1, 2, 3, 59, 5, 6, 7, 60, 9, 10, 11, 12)
    result = outcomes([(tid, 1, numbers)], tuple(range(1, 59)), 1000)[tid]
    assert result.moves == (12, 61, 61)
    assert result.amounts == (100_000, 0, 0)


def test_number_59_can_close_ticket_on_move_28() -> None:
    sequence = (*range(1, 28), 59, *range(28, 58))
    assert closing_moves((*range(1, 12), 59), sequence)[2] == 28


def test_simultaneous_winners_split_each_pool_without_losing_cas() -> None:
    tickets = [(UUID(int=i), i, tuple(range(1, 13))) for i in (3, 1, 2)]
    result = outcomes(tickets, tuple(range(1, 59)), 10_000_000_001)
    assert [sum(r.amounts[c] for r in result.values()) for c in range(3)] == [
        100_000,
        500_000,
        10_000_000_001,
    ]
    assert result[UUID(int=1)].amounts[0] == 33_334
    assert outcomes([], tuple(range(1, 59)), 100) == {}


def test_row_layout_is_immutable_and_every_ticket_inside_cutoff_shares() -> None:
    first = (1, 2, 3, 4, 10, 11, 12, 13, 20, 21, 22, 23)
    second = (1, 10, 20, 2, 3, 11, 21, 4, 12, 13, 22, 23)
    assert BINGO_RULES.validate_combination(second) == second
    result = outcomes(
        [(UUID(int=1), 1, first), (UUID(int=2), 2, second)], tuple(range(1, 59)), 100
    )
    assert result[UUID(int=1)].amounts[:2] == (100_000, 250_000)
    assert result[UUID(int=2)].amounts[:2] == (0, 250_000)
    sequence = generate_sequence()
    assert len(sequence) == len(set(sequence)) == 58
    assert set(sequence) <= set(range(1, 61))


def test_settlement_funds_prizes_and_reset_and_keeps_unwon_jackpot() -> None:
    ticket = SettlementTicket(UUID(int=1), 1, UUID(int=2), tuple(range(1, 13)), 50_000)
    params = dict(
        distribution_balance=0,
        jackpot_balance=10_000_050_000,
        reserve_balance=20_000_000_000,
        base_jackpot=10_000_000_000,
    )
    plan = BINGO_RULES.calculate_settlement([ticket], tuple(range(1, 59)), **params)
    assert plan.jackpot_won and plan.reserve_used == 10_000_600_000
    assert plan.total_payout == 10_000_650_000
    assert plan.jackpot_closing == 10_000_000_000
    assert plan.payouts[0].jackpot_amount == 10_000_050_000
    empty = BINGO_RULES.calculate_settlement([], tuple(range(1, 59)), **params)
    assert not empty.jackpot_won and empty.reserve_used == 0
    assert empty.jackpot_closing == params["jackpot_balance"]
    with pytest.raises(InsufficientReserve):
        BINGO_RULES.calculate_settlement(
            [ticket], tuple(range(1, 59)), **{**params, "reserve_balance": 100}
        )


async def test_quick_purchase_numbers_only_sold_tickets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 9, 14, 12, tzinfo=UTC)
    lottery = Lottery(
        id=UUID(int=10),
        code="bingo",
        name="Kasper Bingo",
        kind=LotteryKind.DAILY,
        ruleset_code="bingo_12_60",
        numbers_to_pick=12,
        max_number=60,
        ticket_price=50_000,
        timezone="Europe/Moscow",
        schedule={},
        sales_cutoff_minutes=2,
        max_tickets_per_purchase=50,
        max_tickets_per_user_per_draw=50,
        is_active=True,
        next_draw_number=2,
        next_ticket_number=101,
    )
    draw = Draw(
        id=UUID(int=20),
        lottery_id=lottery.id,
        public_number=1,
        status=DrawStatus.SCHEDULED,
        scheduled_at=now + timedelta(hours=1),
        sales_close_at=now + timedelta(minutes=58),
        ticket_count=0,
        total_sales=0,
        total_payout=0,
        reserve_used=0,
        configuration_snapshot={"ticket_price": 50_000},
    )
    combinations = [
        [2, 9, 16, 28, 3, 4, 5, 6, 7, 8, 10, 11],
        [2, 9, 16, 28, 12, 13, 14, 15, 17, 18, 19, 20],
    ]
    pool = [
        BingoPoolTicket(
            id=UUID(int=30 + index),
            draw_id=draw.id,
            pool_position=1991 + index,
            numbers=numbers,
        )
        for index, numbers in enumerate(combinations)
    ]
    user_id = UUID(int=40)
    balance = Balance(user_id=user_id, amount=200_000, version=1)
    jackpot = JackpotAccount(
        id=UUID(int=50),
        lottery_id=lottery.id,
        balance=10_000_000_000,
        base_amount=10_000_000_000,
        version=1,
    )
    session = FakeSession(
        scalar_values=[None, lottery, jackpot, None, draw, 0, balance],
        scalar_collections=[pool],
    )
    monkeypatch.setattr("k_loto.application.bingo.ensure_pool", AsyncMock())

    result = await LotteryTicketPurchaseService(
        cast(AsyncSession, session), "bingo", target_draw_id=draw.id
    ).purchase(
        user_id=user_id,
        combinations=[[], []],
        idempotency_key="quick-two",
        pool_required_numbers=(2, 9, 16, 28),
        select_bingo_pool=True,
        now=now,
    )

    tickets = [item for item in session.added if isinstance(item, Ticket)]
    assert [ticket.public_number for ticket in tickets] == [101, 102]
    assert [ticket.numbers for ticket in tickets] == combinations
    assert lottery.next_ticket_number == 103
    assert all(entry.ticket_id for entry in pool)
    assert result.total_cost == 100_000


async def test_draw_starts_once_and_restart_preserves_sequence() -> None:
    now = datetime(2026, 9, 6, 19, tzinfo=UTC)
    draw = Draw(
        id=UUID(int=1),
        lottery_id=UUID(int=2),
        status=DrawStatus.SCHEDULED,
        scheduled_at=now,
        total_payout=0,
    )
    lottery = Lottery(id=UUID(int=2), code="bingo")
    session = FakeSession(
        scalar_values=[lottery, draw, None, JackpotAccount(balance=10_000_000_000)]
    )
    await LotterySettlementService(cast(AsyncSession, session)).settle(draw.id, now=now)
    original = list(draw.winning_numbers or [])
    assert len(original) == 58 and draw.status == DrawStatus.DRAWING
    assert not session.added
    restarted = FakeSession(scalar_values=[lottery, draw, None])
    await LotterySettlementService(cast(AsyncSession, restarted)).settle(
        draw.id, now=now + timedelta(seconds=40)
    )
    assert draw.winning_numbers == original and draw.executed_at == now
    assert not restarted.added


async def test_missed_empty_draw_recovers_immediately_without_a_new_broadcast() -> None:
    now = datetime(2026, 9, 6, 19, tzinfo=UTC)
    draw = Draw(
        id=UUID(int=1),
        lottery_id=UUID(int=2),
        public_number=1,
        status=DrawStatus.SCHEDULED,
        scheduled_at=now - timedelta(days=1),
        total_payout=0,
        configuration_snapshot={},
    )
    lottery = Lottery(
        id=UUID(int=2), code="bingo", name="Kasper Bingo", ruleset_code="bingo_12_60"
    )
    jackpot = JackpotAccount(balance=10_000_000_000, base_amount=10_000_000_000)
    fund = KasperFundAccount(balance=20_000_000_000)
    session = FakeSession(
        scalar_values=[lottery, draw, None, jackpot, lottery, draw, jackpot, fund],
        scalar_collections=[[], [], []],
    )
    result = await LotterySettlementService(cast(AsyncSession, session)).settle(
        draw.id, now=now
    )
    assert not result.already_completed
    assert draw.status == DrawStatus.COMPLETED
    assert draw.executed_at == draw.scheduled_at
    assert len(result.winning_numbers) == 58
    assert jackpot.balance == 10_000_000_000 and result.total_payout == 0
