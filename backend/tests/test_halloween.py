"""Halloween rules and owner-authorized compensating transition regressions."""

from datetime import UTC, datetime, timedelta
from math import comb
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.halloween_transition import HalloweenTransitionService
from k_loto.domain.enums import DrawStatus, TicketStatus, TransactionType
from k_loto.domain.errors import (
    ConfigurationError,
    InvalidStateTransition,
    InvalidTicket,
)
from k_loto.domain.lottery_rules import GROB_RULES, HALLOWEEN_RULES, SettlementTicket
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    Balance,
    Draw,
    JackpotAccount,
    LedgerTransaction,
    Lottery,
    Ticket,
    User,
)
from test_weekly_application import FakeSession

NOW = datetime(2026, 10, 9, 9, tzinfo=UTC)


def test_halloween_pays_only_two_matches_and_splits_the_jackpot() -> None:
    tickets = [
        SettlementTicket(UUID(int=i), i, UUID(int=i + 100), numbers, 6666)
        for i, numbers in enumerate(
            [(4, 5, 6), (1, 5, 6), (1, 2, 28), (1, 2, 3), (1, 2, 3)], 1
        )
    ]
    plan = HALLOWEEN_RULES.calculate_settlement(
        tickets,
        (1, 2, 3),
        distribution_balance=0,
        jackpot_balance=6_666_667,
        reserve_balance=20_000_000,
        base_jackpot=6_666_666,
    )
    assert [p.amount for p in plan.payouts] == [0, 0, 28_000, 3_333_334, 3_333_333]
    assert plan.jackpot_closing == 6_666_666
    assert plan.reserve_used == 6_666_666 + 28_000
    assert comb(28, 3) == 3276
    assert GROB_RULES.max_number == 16
    assert GROB_RULES.fixed_payouts == {1: 666, 2: 6666}


def test_halloween_purchase_uses_integer_price_and_all_revenue_to_jackpot() -> None:
    quote = HALLOWEEN_RULES.quote_purchase([[28, 1, 7]], 6666, 10_000)
    assert quote.combinations == ((1, 7, 28),)
    assert quote.total_cost == quote.jackpot_contribution == 6666
    assert quote.distribution_contribution == 0


@pytest.mark.parametrize("numbers", [[1, 2, 29], [1, 1, 28], [1, 2], [True, 2, 3]])
def test_halloween_rejects_invalid_selections(numbers: list[int]) -> None:
    with pytest.raises(InvalidTicket):
        HALLOWEEN_RULES.validate_combination(numbers)


def objects() -> tuple[User, Lottery, Draw, Ticket, JackpotAccount, Balance]:
    owner = User(id=UUID(int=1), is_admin=True)
    lottery = Lottery(
        id=UUID(int=2),
        code="grob",
        name="ГРОБ",
        ruleset_code=GROB_RULES.code,
        numbers_to_pick=3,
        max_number=16,
        ticket_price=6666,
    )
    draw = Draw(
        id=UUID(int=3),
        status=DrawStatus.SCHEDULED,
        scheduled_at=NOW + timedelta(hours=1),
        winning_numbers=None,
        executed_at=None,
        ticket_count=1,
        total_sales=6666,
        configuration_snapshot={"ruleset_code": GROB_RULES.code, "max_number": 16},
    )
    ticket = Ticket(
        id=UUID(int=4),
        user_id=owner.id,
        draw_id=draw.id,
        public_number=1,
        purchase_price=6666,
        status=TicketStatus.PURCHASED,
        numbers=[1, 2, 16],
        prize_amount=0,
    )
    jackpot = JackpotAccount(
        id=UUID(int=5), balance=7_000_000, base_amount=6_666_666, version=1
    )
    balance = Balance(user_id=owner.id, amount=100, version=1)
    return owner, lottery, draw, ticket, jackpot, balance


async def test_transition_preserves_ticket_and_balances_every_refund() -> None:
    owner, lottery, draw, ticket, jackpot, balance = objects()
    session = FakeSession(
        scalar_values=[owner, lottery, jackpot],
        scalar_collections=[[draw], [ticket], [balance]],
    )
    result = await HalloweenTransitionService(cast(AsyncSession, session)).activate(
        owner_id=owner.id, now=NOW
    )
    assert (result.refunded_tickets, result.refunded_cas, result.converted_draws) == (
        1,
        6666,
        1,
    )
    assert ticket.status == TicketStatus.REFUNDED
    assert ticket.numbers == [1, 2, 16]
    assert ticket.settled_at == NOW
    assert jackpot.balance == 7_000_000 - 6666
    assert balance.amount == 6766
    assert draw.ticket_count == draw.total_sales == 0
    assert draw.configuration_snapshot["ruleset_code"] == HALLOWEEN_RULES.code
    assert lottery.max_number == 28
    entries = [item for item in session.added if isinstance(item, LedgerTransaction)]
    assert len(entries) == 2 and sum(item.amount for item in entries) == 0
    assert all(item.type == TransactionType.TICKET_REFUND for item in entries)
    assert all(item.ticket_id == ticket.id for item in entries)
    assert entries[0].operation_id == entries[1].operation_id
    audits = [item for item in session.added if isinstance(item, AdminAuditLog)]
    assert len(audits) == 3


async def test_transition_is_idempotent() -> None:
    owner, lottery, *_ = objects()
    lottery.ruleset_code = HALLOWEEN_RULES.code
    session = FakeSession(scalar_values=[owner, lottery])
    result = await HalloweenTransitionService(cast(AsyncSession, session)).activate(
        owner_id=owner.id, now=NOW
    )
    assert result.already_processed and result.refunded_cas == 0
    assert not session.added


@pytest.mark.parametrize(
    "status", [DrawStatus.COMPLETED, DrawStatus.DRAWING, DrawStatus.FAILED]
)
async def test_transition_refuses_started_or_completed_draws(
    status: DrawStatus,
) -> None:
    owner, lottery, draw, *_ = objects()
    draw.status = status
    session = FakeSession(scalar_values=[owner, lottery], scalar_collections=[[draw]])
    with pytest.raises(InvalidStateTransition):
        await HalloweenTransitionService(cast(AsyncSession, session)).activate(
            owner_id=owner.id, now=NOW
        )
    assert not session.added


async def test_transition_requires_due_draw_recovery() -> None:
    owner, lottery, draw, *_ = objects()
    draw.scheduled_at = NOW
    session = FakeSession(scalar_values=[owner, lottery], scalar_collections=[[draw]])
    with pytest.raises(InvalidStateTransition):
        await HalloweenTransitionService(cast(AsyncSession, session)).activate(
            owner_id=owner.id, now=NOW
        )
    assert lottery.ruleset_code == GROB_RULES.code


async def test_transition_insufficient_jackpot_makes_no_refund() -> None:
    owner, lottery, draw, ticket, jackpot, _ = objects()
    jackpot.balance = 1
    session = FakeSession(
        scalar_values=[owner, lottery, jackpot], scalar_collections=[[draw], [ticket]]
    )
    with pytest.raises(ConfigurationError):
        await HalloweenTransitionService(cast(AsyncSession, session)).activate(
            owner_id=owner.id, now=NOW
        )
    assert ticket.status == TicketStatus.PURCHASED
    assert not session.added


async def test_transition_requires_authorized_audit_actor() -> None:
    session = FakeSession(scalar_values=[None])
    with pytest.raises(ConfigurationError):
        await HalloweenTransitionService(cast(AsyncSession, session)).activate(
            owner_id=UUID(int=1), now=NOW
        )
    assert not session.added
