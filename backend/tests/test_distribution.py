"""Roll-down rules, immutable purchased tickets and excluded Dual."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.distribution import (
    DistributionDrawService,
    announcement_text,
    projected_id,
    validate_assignment,
)
from k_loto.domain.distribution import distribute_jackpot
from k_loto.domain.enums import DrawStatus
from k_loto.domain.errors import InsufficientReserve
from k_loto.domain.lottery_rules import (
    GRAND_FIXED_RULES,
    SettlementTicket,
)
from test_weekly_application import build_purchase_accounts

NOW = datetime(2026, 10, 9, tzinfo=UTC)
WINNING = (1, 2, 3, 4, 5, 36, 37)


def ticket(number: int, primary: int, secondary: int) -> SettlementTicket:
    numbers = tuple(
        list(range(1, primary + 1))
        + list(range(6, 6 + 5 - primary))
        + list(range(36, 36 + secondary))
        + list(range(38, 38 + 2 - secondary))
    )
    return SettlementTicket(UUID(int=number), number, UUID(int=100), numbers, 50_000)


def settle(tickets, pool=101):
    return GRAND_FIXED_RULES.calculate_settlement(
        tickets,
        WINNING,
        distribution_balance=0,
        jackpot_balance=pool,
        reserve_balance=100_000_000,
        base_jackpot=1_000,
    )


@pytest.mark.parametrize(
    "primary,secondary", [(k // 10, k % 10) for k in GRAND_FIXED_RULES.fixed_payouts]
)
def test_every_grand_category_receives_full_pool(primary, secondary):
    tickets = [
        ticket(2, primary, secondary),
        ticket(1, primary, secondary),
        ticket(3, 0, 0),
    ]
    original = settle(tickets)
    plan = distribute_jackpot(
        original,
        tickets,
        GRAND_FIXED_RULES,
        base_jackpot=1_000,
        fund_balance=100_000_000,
    )
    payouts = {p.ticket_id: p for p in plan.payouts}
    ordinary = GRAND_FIXED_RULES.fixed_payouts[primary * 10 + secondary]
    assert payouts[UUID(int=1)].amount == ordinary + 51
    assert payouts[UUID(int=2)].amount == ordinary + 50
    assert payouts[UUID(int=3)].amount == 0
    assert plan.total_payout == original.total_payout + 101
    assert plan.jackpot_closing == plan.jackpot_reset_credit == 1_000
    assert plan.reserve_used == original.reserve_used + 1_000
    assert plan.jackpot_distributed and not plan.jackpot_won
    assert plan.distribution_category == str(primary * 10 + secondary)


def test_skips_empty_categories_and_retains_lower_ordinary_prizes():
    tickets = [ticket(1, 4, 0), ticket(2, 3, 2)]
    plan = distribute_jackpot(
        settle(tickets),
        tickets,
        GRAND_FIXED_RULES,
        base_jackpot=1_000,
        fund_balance=100_000_000,
    )
    assert plan.distribution_category == "40"
    assert [p.amount for p in plan.payouts] == [500_101, 300_000]


def test_all_paid_tickets_share_when_no_categories_win():
    tickets = [ticket(3, 0, 0), ticket(1, 1, 0), ticket(2, 0, 1)]
    plan = distribute_jackpot(
        settle(tickets),
        tickets,
        GRAND_FIXED_RULES,
        base_jackpot=1_000,
        fund_balance=100_000_000,
    )
    assert plan.distribution_category == "all"
    assert [p.amount for p in plan.payouts] == [34, 34, 33]
    assert sum(p.jackpot_amount for p in plan.payouts) == 101


def test_actual_jackpot_winner_and_empty_draw_keep_normal_rules():
    for tickets in ([], [ticket(1, 5, 2)]):
        original = settle(tickets)
        assert (
            distribute_jackpot(
                original,
                tickets,
                GRAND_FIXED_RULES,
                base_jackpot=1_000,
                fund_balance=100_000_000,
            )
            is original
        )


def test_insufficient_fund_cannot_reset_or_partially_pay():
    tickets = [ticket(1, 0, 0)]
    original = settle(tickets)
    with pytest.raises(InsufficientReserve):
        distribute_jackpot(
            original, tickets, GRAND_FIXED_RULES, base_jackpot=1_000, fund_balance=999
        )
    assert original.jackpot_closing == 101 and original.total_payout == 0


def test_bingo_uses_tour_categories_instead_of_raw_match_count():
    from k_loto.domain.lottery_rules import BINGO_RULES, TicketPayout

    tickets = [ticket(1, 0, 0), ticket(2, 0, 0)]
    original = replace(
        settle(tickets),
        reserve_used=30,
        total_payout=30,
        payouts=(
            TicketPayout(
                tickets[0].id, 1, tickets[0].user_id, 10, 10, 0, {"amounts": [10, 0, 0]}
            ),
            TicketPayout(
                tickets[1].id, 2, tickets[1].user_id, 9, 20, 0, {"amounts": [0, 20, 0]}
            ),
        ),
    )
    plan = distribute_jackpot(
        original, tickets, BINGO_RULES, base_jackpot=1_000, fund_balance=100_000_000
    )
    assert plan.distribution_category == "bingo-tour-2"
    assert [p.amount for p in plan.payouts] == [10, 121]


@pytest.mark.parametrize("code", ["dual", "kasper-live", "aurora", "vault"])
def test_excluded_games_cannot_be_assigned(code):
    _, lottery, draw, *_ = build_purchase_accounts(NOW)
    lottery.code = code
    with pytest.raises(ValueError, match="не участвует"):
        validate_assignment(draw, lottery, NOW)


def test_existing_tickets_are_eligible_until_exact_cutoff():
    _, lottery, draw, *_ = build_purchase_accounts(NOW)
    draw.ticket_count = 145
    validate_assignment(draw, lottery, draw.sales_close_at - timedelta(microseconds=1))
    assert draw.ticket_count == 145
    with pytest.raises(ValueError, match="окончания продаж"):
        validate_assignment(draw, lottery, draw.sales_close_at)
    draw.status = DrawStatus.COMPLETED
    with pytest.raises(ValueError):
        validate_assignment(draw, lottery, NOW)


async def test_dual_is_rejected_even_on_replayed_preexisting_flag():
    _, lottery, draw, *_ = build_purchase_accounts(NOW)
    lottery.code = "dual"
    draw.is_distribution = True

    class Session:
        from test_weekly_application import TransactionContext

        def begin(self):
            return self.TransactionContext()

        async def scalar(self, _statement):
            return draw

        async def get(self, _model, _key):
            return lottery

    with pytest.raises(ValueError, match="не участвует"):
        await DistributionDrawService(cast(AsyncSession, Session())).assign(
            draw.id, UUID(int=1)
        )


def test_announcement_is_text_only_moscow_and_mentions_existing_tickets():
    text = announcement_text("Casper Grand", "weekly", 10, NOW, 5_000_000)
    assert "09.10.2026 в 03:00 МСК" in text
    assert "5 000 000 CAS" in text and "#CasperGrand" in text
    assert "Он тоже участвует" in text and "все купленные билеты" in text


async def test_future_preparation_creates_every_official_draw_in_order():
    from test_weekly_application import FakeSession

    _, lottery, latest, _, jackpot, _ = build_purchase_accounts(NOW)
    latest.scheduled_at = datetime(2099, 10, 4, 17, tzinfo=UTC)
    from k_loto.domain.schedules import next_draw_at

    first = next_draw_at(lottery.kind, latest.scheduled_at, lottery.schedule)
    target = next_draw_at(lottery.kind, first, lottery.schedule)
    session = FakeSession(scalar_values=[lottery, None, latest, jackpot])
    target_id = projected_id(lottery.id, target)
    assert (
        await DistributionDrawService(cast(AsyncSession, session)).prepare(
            lottery.id, target, target_id
        )
        == target_id
    )
    assert [d.scheduled_at for d in session.added] == [first, target]
    assert [d.public_number for d in session.added] == [2, 3]
    assert lottery.next_draw_number == 4


async def test_calendar_race_reuses_draw_prepared_by_scheduler():
    from test_weekly_application import FakeSession

    _, lottery, draw, *_ = build_purchase_accounts(NOW)
    original_id = draw.id
    session = FakeSession(scalar_values=[lottery, draw])
    result = await DistributionDrawService(cast(AsyncSession, session)).prepare(
        lottery.id, draw.scheduled_at, projected_id(lottery.id, draw.scheduled_at)
    )
    assert result == original_id and session.added == []


async def test_assignment_replay_has_one_post_audit_and_no_money_writes():
    from types import SimpleNamespace
    from unittest.mock import patch

    from k_loto.infrastructure.database.models import (
        AdminAuditLog,
        DistributionAnnouncement,
    )
    from test_weekly_application import FakeSession

    _, lottery, draw, *_ = build_purchase_accounts(NOW)
    draw.ticket_count = 145

    class Session(FakeSession):
        async def get(self, *_args, **_kwargs):
            return lottery

    session = Session(scalar_values=[draw, 1001, None])
    with patch(
        "k_loto.application.distribution.get_settings",
        return_value=SimpleNamespace(
            lottery_bot_token=True, publication_channel="@mock"
        ),
    ):
        result = await DistributionDrawService(cast(AsyncSession, session)).assign(
            draw.id, UUID(int=99), now=NOW
        )
    assert result["ticket_count"] == 145 and result["is_distribution"]
    assert [type(v) for v in session.added] == [DistributionAnnouncement, AdminAuditLog]
    session.scalar_values = iter([draw, 1001, session.added[0]])
    result2 = await DistributionDrawService(cast(AsyncSession, session)).assign(
        draw.id, UUID(int=99), now=NOW
    )
    assert result2 == result and len(session.added) == 2
