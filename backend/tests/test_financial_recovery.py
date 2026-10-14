"""Regression coverage for the first financial audit remediation stage."""

from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.admin import AdminMutationService
from k_loto.application.instant import InstantTicketPurchaseService
from k_loto.application.purchase_guard import bingo_purchase_key
from k_loto.application.purchase_receipts import PurchaseReceiptService
from k_loto.application.weekly import (
    LotteryTicketPurchaseService,
    WeeklySettlementService,
    WeeklyTicketPurchaseService,
)
from k_loto.domain.enums import DrawStatus, TicketStatus
from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientReserve,
    InvalidStateTransition,
    InvalidTicket,
    NoAvailableDraw,
)
from k_loto.domain.instant import INSTANT_GAMES
from k_loto.infrastructure.database.models import (
    KasperFundAccount,
    LedgerTransaction,
    Ticket,
)
from test_purchase_recovery import ReceiptSession
from test_weekly_application import FakeSession, FixedGenerator, build_purchase_accounts


async def test_bingo_cancellation_uses_unhashed_client_key() -> None:
    session = ReceiptSession([UUID(int=9)])
    with pytest.raises(InvalidTicket, match="cancelled"):
        await LotteryTicketPurchaseService(
            cast(AsyncSession, session), "bingo"
        ).purchase(user_id=UUID(int=1), combinations=[[]], idempotency_key="m1-bingo")
    session.execute.assert_awaited_once()
    assert session.added == []


async def test_historical_bingo_receipt_is_included_in_owner_scoped_lookup() -> None:
    session = ReceiptSession([None])
    user = UUID(int=1)
    await PurchaseReceiptService(cast(AsyncSession, session)).find(
        user, "m1-bingo", "scheduled"
    )
    params = session.scalar.call_args.args[0].compile().params
    assert [
        "purchase:m1-bingo:user",
        f"purchase:{bingo_purchase_key(user, 'm1-bingo')}:user",
    ] in params.values()


async def test_purchase_does_not_create_or_sell_a_missed_draw() -> None:
    now = datetime(2026, 10, 14, 12, tzinfo=UTC)
    user, lottery, draw, balance, jackpot, _ = build_purchase_accounts(now)
    draw.scheduled_at = datetime(2026, 9, 20, 17, tzinfo=UTC)
    session = FakeSession(scalar_values=[None, lottery, jackpot, None, None, draw])
    with pytest.raises(NoAvailableDraw, match="recovery"):
        await WeeklyTicketPurchaseService(cast(AsyncSession, session)).purchase(
            user_id=user,
            combinations=[[1, 2, 3, 4, 5]],
            idempotency_key="late-recovery",
            now=now,
        )
    assert session.added == []
    assert balance.amount == 1000 and jackpot.balance == 2000


async def test_settlement_failure_reuses_committed_outcome() -> None:
    now = datetime(2026, 10, 14, 12, tzinfo=UTC)
    user, lottery, draw, balance, jackpot, _ = build_purchase_accounts(now)
    draw.scheduled_at = now - timedelta(minutes=1)
    ticket = Ticket(
        id=UUID(int=123),
        user_id=user,
        draw_id=draw.id,
        public_number=1,
        numbers=[1, 2, 3, 4, 5],
        purchase_price=100,
        status=TicketStatus.PURCHASED,
    )
    fund = KasperFundAccount(balance=0, version=1)
    generator = FixedGenerator()
    for attempt in range(2):
        prep = [lottery, draw, None] + ([jackpot] if attempt == 0 else [])
        session = FakeSession(
            scalar_values=[*prep, lottery, draw, jackpot, fund],
            scalar_collections=[[ticket]],
        )
        with pytest.raises(InsufficientReserve):
            await WeeklySettlementService(
                cast(AsyncSession, session), generator
            ).settle(draw.id, now=now)
        assert draw.winning_numbers == [1, 2, 3, 4, 5]
        assert draw.status == DrawStatus.DRAWING
        assert session.added == [] and balance.amount == 1000
    assert generator.calls == 1


async def test_later_draw_cannot_overtake_unpaid_earlier_outcome() -> None:
    now = datetime(2026, 10, 14, 12, tzinfo=UTC)
    _, lottery, draw, _, _, _ = build_purchase_accounts(now)
    draw.scheduled_at = now
    generator = FixedGenerator()
    session = FakeSession(scalar_values=[lottery, draw, UUID(int=9)])
    with pytest.raises(InvalidStateTransition, match="Earlier"):
        await WeeklySettlementService(cast(AsyncSession, session), generator).settle(
            draw.id, now=now
        )
    assert generator.calls == 0


async def test_admin_cannot_spend_committed_jackpot() -> None:
    now = datetime(2026, 10, 14, 12, tzinfo=UTC)
    _, lottery, _, _, jackpot, _ = build_purchase_accounts(now)
    session = FakeSession(scalar_values=[None, lottery, jackpot, 2000])
    with pytest.raises(ValueError, match="committed"):
        await AdminMutationService(
            cast(AsyncSession, session), UUID(int=42)
        ).set_jackpot(
            lottery.id,
            target_amount=1999,
            reason="audit regression",
            idempotency_key="reduce-locked",
        )
    assert jackpot.balance == 2000 and session.added == []


async def test_underfunded_committed_jackpot_cannot_mint_money() -> None:
    now = datetime(2026, 10, 14, 12, tzinfo=UTC)
    _, lottery, draw, _, jackpot, _ = build_purchase_accounts(now)
    draw.scheduled_at = now
    draw.status = DrawStatus.DRAWING
    draw.winning_numbers = [1, 2, 3, 4, 5]
    draw.jackpot_opening = jackpot.balance + 100
    session = FakeSession(
        scalar_values=[
            lottery,
            draw,
            None,
            lottery,
            draw,
            jackpot,
            KasperFundAccount(balance=1_000_000),
        ],
        scalar_collections=[[]],
    )
    with pytest.raises(ConfigurationError, match="obligation"):
        await WeeklySettlementService(cast(AsyncSession, session)).settle(
            draw.id, now=now
        )
    assert not any(isinstance(item, LedgerTransaction) for item in session.added)


@pytest.mark.parametrize("game", INSTANT_GAMES)
@pytest.mark.parametrize("quantity", [1, 3])
async def test_instant_solvency_is_checked_before_randomness(game, quantity) -> None:
    now = datetime(2026, 10, 14, 12, tzinfo=UTC)
    user, _, _, balance, _, _ = build_purchase_accounts(now)
    balance.amount = 1_000_000
    rules = INSTANT_GAMES[game]
    fund = KasperFundAccount(balance=quantity * max(b.prize for b in rules.bands) - 1)
    session = FakeSession(scalar_values=[None, fund, balance, None])
    generator = AsyncMock()
    with pytest.raises(ConfigurationError, match="every possible"):
        await InstantTicketPurchaseService(
            cast(AsyncSession, session), generator, game_code=game
        ).purchase(user_id=user, quantity=quantity, idempotency_key="insolvent")
    generator.draw_sequence.assert_not_called()
    assert session.added == [] and balance.amount == 1_000_000
