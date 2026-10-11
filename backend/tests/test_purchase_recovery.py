"""Receipts, cancellation fences and draw binding must not alter money/history."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.purchase_guard import guard_attempt
from k_loto.application.purchase_receipts import PurchaseReceiptService
from k_loto.application.weekly import WeeklyTicketPurchaseService
from k_loto.domain.errors import InvalidTicket, NoAvailableDraw
from k_loto.infrastructure.database.models import PurchaseCancellation
from test_weekly_application import FakeSession, build_purchase_accounts


class ReceiptSession:
    def __init__(self, values: list[Any]) -> None:
        self.scalar = AsyncMock(side_effect=values)
        self.execute = AsyncMock()
        self.added: list[Any] = []

    @asynccontextmanager
    async def begin(self):
        yield

    def add(self, value: Any) -> None:
        self.added.append(value)


async def test_cancel_fences_only_an_uncommitted_request() -> None:
    fake = ReceiptSession([None, None])
    service = PurchaseReceiptService(cast(AsyncSession, fake))
    assert (
        await service.cancel_uncommitted(UUID(int=1), "m1-request", "scheduled") is None
    )
    fake.execute.assert_awaited_once()
    assert len(fake.added) == 1
    assert isinstance(fake.added[0], PurchaseCancellation)
    assert fake.added[0].key == "m1-request"


async def test_cancel_committed_request_returns_receipt_without_a_fence(
    monkeypatch,
) -> None:
    fake = ReceiptSession([])
    service = PurchaseReceiptService(cast(AsyncSession, fake))
    receipt = object()
    monkeypatch.setattr(service, "find", AsyncMock(return_value=receipt))
    assert (
        await service.cancel_uncommitted(UUID(int=1), "m1-request", "scheduled")
        is receipt
    )
    assert fake.added == []


async def test_cancel_is_idempotent() -> None:
    fake = ReceiptSession([None, UUID(int=3)])
    assert (
        await PurchaseReceiptService(cast(AsyncSession, fake)).cancel_uncommitted(
            UUID(int=1), "m1-request", "vault"
        )
        is None
    )
    assert fake.added == []


async def test_old_client_cannot_cancel_its_unfenced_request() -> None:
    fake = ReceiptSession([])
    with pytest.raises(ValueError):
        await PurchaseReceiptService(cast(AsyncSession, fake)).cancel_uncommitted(
            UUID(int=1), "old-key", "scheduled"
        )
    fake.execute.assert_not_awaited()


async def test_cancelled_key_is_rejected_before_any_purchase_changes() -> None:
    fake = ReceiptSession([UUID(int=2)])
    with pytest.raises(InvalidTicket, match="cancelled"):
        await guard_attempt(
            cast(AsyncSession, fake), UUID(int=1), "m1-request", "scheduled"
        )
    assert fake.added == []
    fake.execute.assert_awaited_once()


async def test_receipt_query_is_owner_scoped() -> None:
    fake = ReceiptSession([None])
    assert (
        await PurchaseReceiptService(cast(AsyncSession, fake)).find(
            UUID(int=1), "m1-request", "scheduled"
        )
        is None
    )
    statement = str(fake.scalar.call_args.args[0])
    assert "ledger_transactions.user_id =" in statement
    assert "ledger_transactions.account_id =" in statement
    assert fake.added == []
    fake.execute.assert_not_awaited()


async def test_retry_does_not_buy_into_a_different_draw() -> None:
    now = datetime(2026, 10, 11, tzinfo=UTC)
    user, lottery, draw, balance, jackpot, _ = build_purchase_accounts(now)
    fake = FakeSession(scalar_values=[None, lottery, jackpot, None, draw])
    with pytest.raises(NoAvailableDraw, match="originally selected"):
        await WeeklyTicketPurchaseService(cast(AsyncSession, fake)).purchase(
            user_id=user,
            combinations=[[1, 2, 3, 4, 5]],
            idempotency_key="old-key",
            expected_scheduled_at=now - timedelta(hours=1),
            now=now,
        )
    assert balance.amount == 1000
    assert jackpot.balance == 2000
    assert fake.added == []
