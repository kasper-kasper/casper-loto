"""Unit tests for Weekly transactional orchestration without a live database."""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.daily import DailySettlementService, DailyTicketPurchaseService
from k_loto.application.weekly import (
    WeeklySettlementService,
    WeeklyTicketPurchaseService,
)
from k_loto.domain.enums import (
    DrawStatus,
    LedgerAccountKind,
    LotteryKind,
    NotificationType,
    TransactionType,
)
from k_loto.domain.errors import InvalidStateTransition, InvalidTicket
from k_loto.infrastructure.database.models import (
    Balance,
    DistributionFund,
    Draw,
    JackpotAccount,
    LedgerTransaction,
    Lottery,
    LotteryReserve,
    NotificationOutbox,
    Ticket,
)


class TransactionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: object) -> None:
        return None


class ScalarCollection:
    def __init__(self, values: Iterable[Any]) -> None:
        self._values = list(values)

    def all(self) -> list[Any]:
        return self._values


class FakeSession:
    def __init__(
        self,
        *,
        scalar_values: Iterable[Any],
        scalar_collections: Iterable[Iterable[Any]] = (),
    ) -> None:
        self.scalar_values = iter(scalar_values)
        self.scalar_collections = iter(scalar_collections)
        self.added: list[Any] = []

    def begin(self) -> TransactionContext:
        return TransactionContext()

    async def scalar(self, _statement: object) -> Any:
        return next(self.scalar_values)

    async def scalars(self, _statement: object) -> ScalarCollection:
        return ScalarCollection(next(self.scalar_collections))

    def add(self, value: Any) -> None:
        self.added.append(value)

    def add_all(self, values: Iterable[Any]) -> None:
        self.added.extend(values)


class FixedGenerator:
    def __init__(self) -> None:
        self.calls = 0

    def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]:
        self.calls += 1
        assert (population_size, numbers_to_pick) == (20, 5)
        return (1, 2, 3, 4, 5)


class FixedDailyGenerator:
    def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]:
        assert (population_size, numbers_to_pick) == (15, 4)
        return (1, 2, 3, 4)


def build_purchase_accounts(now: datetime):
    lottery_id = UUID(int=100)
    user_id = UUID(int=200)
    draw_id = UUID(int=300)
    lottery = Lottery(
        id=lottery_id,
        code="weekly",
        name="Weekly 5/20",
        kind=LotteryKind.WEEKLY,
        numbers_to_pick=5,
        max_number=20,
        ticket_price=100,
        timezone="Europe/Moscow",
        schedule={},
        sales_cutoff_minutes=5,
        max_tickets_per_purchase=1000,
        max_tickets_per_user_per_draw=5000,
        is_active=True,
        next_draw_number=2,
        next_ticket_number=11,
    )
    draw = Draw(
        id=draw_id,
        lottery_id=lottery_id,
        public_number=1,
        status=DrawStatus.SCHEDULED,
        scheduled_at=now + timedelta(hours=1),
        sales_close_at=now + timedelta(minutes=55),
        correlation_id=UUID(int=400),
        ticket_count=0,
        total_sales=0,
        total_payout=0,
        reserve_used=0,
    )
    balance = Balance(user_id=user_id, amount=1_000, version=1)
    jackpot = JackpotAccount(
        id=UUID(int=500),
        lottery_id=lottery_id,
        balance=2_000,
        base_amount=1_000,
        version=1,
    )
    distribution = DistributionFund(
        id=UUID(int=600), lottery_id=lottery_id, balance=300, version=1
    )
    return user_id, lottery, draw, balance, jackpot, distribution


async def test_purchase_rejects_more_than_limit_before_database() -> None:
    service = WeeklyTicketPurchaseService(
        cast(AsyncSession, FakeSession(scalar_values=[]))
    )

    with pytest.raises(InvalidTicket, match="1 to 1000"):
        await service.purchase(
            user_id=UUID(int=1),
            combinations=[[1, 2, 3, 4, 5]] * 1001,
            idempotency_key="too-many",
        )


async def test_multi_ticket_purchase_updates_all_accounts_and_numbering() -> None:
    now = datetime(2026, 8, 14, 17, tzinfo=UTC)
    user_id, lottery, draw, balance, jackpot, distribution = build_purchase_accounts(
        now
    )
    fake = FakeSession(
        scalar_values=[None, lottery, None, draw, 0, balance, jackpot, distribution]
    )
    service = WeeklyTicketPurchaseService(cast(AsyncSession, fake))

    result = await service.purchase(
        user_id=user_id,
        combinations=[[1, 2, 3, 4, 5], [1, 2, 3, 4, 5]],
        idempotency_key="checkout-1",
        now=now,
    )

    created_tickets = [item for item in fake.added if isinstance(item, Ticket)]
    ledger = [item for item in fake.added if isinstance(item, LedgerTransaction)]
    assert [item.public_number for item in created_tickets] == [11, 12]
    assert balance.amount == 800
    assert jackpot.balance == 2_100
    assert distribution.balance == 400
    assert lottery.next_ticket_number == 13
    assert draw.ticket_count == 2
    assert draw.total_sales == 200
    assert result.total_cost == 200
    assert len(ledger) == 3
    assert sum(item.amount for item in ledger) == 0
    notifications = [
        item for item in fake.added if isinstance(item, NotificationOutbox)
    ]
    assert len(notifications) == 1
    assert notifications[0].type == NotificationType.TICKET_PURCHASED
    assert len(notifications[0].payload["tickets"]) == 2


async def test_five_draw_purchase_is_prepaid_and_created_atomically() -> None:
    now = datetime(2026, 8, 14, 17, tzinfo=UTC)
    user_id, lottery, draw, balance, jackpot, distribution = build_purchase_accounts(
        now
    )
    fake = FakeSession(
        scalar_values=[
            None,
            lottery,
            None,
            draw,
            0,
            0,
            0,
            0,
            0,
            balance,
            jackpot,
            distribution,
        ],
        scalar_collections=[[draw]],
    )

    result = await WeeklyTicketPurchaseService(cast(AsyncSession, fake)).purchase(
        user_id=user_id,
        combinations=[[1, 2, 3, 4, 5]],
        idempotency_key="five-draws",
        draw_count=5,
        now=now,
    )

    created_draws = [item for item in fake.added if isinstance(item, Draw)]
    created_tickets = [item for item in fake.added if isinstance(item, Ticket)]
    assert len(created_draws) == 4
    assert len(created_tickets) == 5
    assert len({ticket.draw_id for ticket in created_tickets}) == 5
    assert result.draw_count == 5
    assert len(result.draw_ids) == 5
    assert result.total_cost == 500
    assert balance.amount == 500
    assert jackpot.balance == 2_250
    assert distribution.balance == 550


async def test_daily_purchase_uses_40_60_split_and_independent_numbering() -> None:
    now = datetime(2026, 8, 14, 12, tzinfo=UTC)
    user_id, lottery, draw, balance, jackpot, distribution = build_purchase_accounts(
        now
    )
    lottery.code = "daily"
    lottery.name = "Daily 4/15"
    lottery.kind = LotteryKind.DAILY
    lottery.numbers_to_pick = 4
    lottery.max_number = 15
    lottery.sales_cutoff_minutes = 2
    lottery.next_ticket_number = 50
    draw.scheduled_at = datetime(2026, 8, 14, 15, tzinfo=UTC)
    draw.sales_close_at = datetime(2026, 8, 14, 14, 58, tzinfo=UTC)
    fake = FakeSession(
        scalar_values=[None, lottery, None, draw, 0, balance, jackpot, distribution]
    )

    result = await DailyTicketPurchaseService(cast(AsyncSession, fake)).purchase(
        user_id=user_id,
        combinations=[[1, 2, 3, 4], [1, 2, 3, 4]],
        idempotency_key="daily-checkout",
        now=now,
    )

    tickets = [item for item in fake.added if isinstance(item, Ticket)]
    assert [item.public_number for item in tickets] == [50, 51]
    assert jackpot.balance == 2_080
    assert distribution.balance == 420
    assert balance.amount == 800
    assert result.total_cost == 200


async def test_empty_daily_draw_settlement_is_completed_idempotently() -> None:
    now = datetime(2026, 8, 14, 12, tzinfo=UTC)
    _, lottery, draw, _, jackpot, distribution = build_purchase_accounts(now)
    lottery.code = "daily"
    lottery.name = "Daily 4/15"
    lottery.kind = LotteryKind.DAILY
    lottery.numbers_to_pick = 4
    lottery.max_number = 15
    draw.scheduled_at = now
    reserve = LotteryReserve(
        id=UUID(int=700), lottery_id=lottery.id, balance=1_000, version=1
    )
    fake = FakeSession(
        scalar_values=[draw, lottery, jackpot, distribution, reserve],
        scalar_collections=[[], [], []],
    )

    result = await DailySettlementService(
        cast(AsyncSession, fake), FixedDailyGenerator()
    ).settle(draw.id, now=now)

    assert result.winning_numbers == (1, 2, 3, 4)
    assert draw.status == DrawStatus.COMPLETED
    assert draw.total_payout == 0


async def test_duplicate_purchase_idempotency_key_returns_original_result() -> None:
    operation_id = UUID(int=1)
    draw_id = UUID(int=2)
    ticket_id = UUID(int=3)
    existing = LedgerTransaction(
        id=UUID(int=4),
        operation_id=operation_id,
        idempotency_key="purchase:same:user",
        account_kind=LedgerAccountKind.USER_BALANCE,
        account_id=UUID(int=5),
        type=TransactionType.TICKET_PURCHASE,
        amount=-100,
        balance_before=500,
        balance_after=400,
        details={"draw_id": str(draw_id), "ticket_ids": [str(ticket_id)]},
    )
    fake = FakeSession(scalar_values=[existing])
    service = WeeklyTicketPurchaseService(cast(AsyncSession, fake))

    result = await service.purchase(
        user_id=UUID(int=5),
        combinations=[[1, 2, 3, 4, 5]],
        idempotency_key="same",
    )

    assert result.already_processed
    assert result.operation_id == operation_id
    assert result.ticket_ids == (ticket_id,)
    assert fake.added == []


async def test_purchase_after_cutoff_creates_and_uses_next_weekly_draw() -> None:
    now = datetime(2026, 8, 16, 16, 56, tzinfo=UTC)
    user_id, lottery, closing_draw, balance, jackpot, distribution = (
        build_purchase_accounts(now)
    )
    closing_draw.scheduled_at = datetime(2026, 8, 16, 17, tzinfo=UTC)
    closing_draw.sales_close_at = datetime(2026, 8, 16, 16, 55, tzinfo=UTC)
    lottery.next_draw_number = 2
    fake = FakeSession(
        scalar_values=[
            None,
            lottery,
            None,
            None,
            closing_draw,
            0,
            balance,
            jackpot,
            distribution,
        ]
    )

    result = await WeeklyTicketPurchaseService(cast(AsyncSession, fake)).purchase(
        user_id=user_id,
        combinations=[[1, 2, 3, 4, 5]],
        idempotency_key="after-cutoff",
        now=now,
    )

    created_draws = [item for item in fake.added if isinstance(item, Draw)]
    assert len(created_draws) == 1
    next_draw = created_draws[0]
    assert next_draw.public_number == 2
    assert next_draw.scheduled_at == datetime(2026, 8, 23, 17, tzinfo=UTC)
    assert result.draw_id == next_draw.id
    assert lottery.next_draw_number == 3


async def test_empty_draw_settlement_completes_and_uses_secure_generator() -> None:
    now = datetime(2026, 8, 14, 17, tzinfo=UTC)
    execution_time = now + timedelta(hours=2)
    _, lottery, draw, _, jackpot, distribution = build_purchase_accounts(now)
    reserve = LotteryReserve(
        id=UUID(int=700), lottery_id=lottery.id, balance=1_000, version=1
    )
    fake = FakeSession(
        scalar_values=[draw, lottery, jackpot, distribution, reserve],
        scalar_collections=[[], [], []],
    )
    generator = FixedGenerator()
    service = WeeklySettlementService(cast(AsyncSession, fake), generator)

    result = await service.settle(draw.id, now=execution_time)

    assert result.winning_numbers == (1, 2, 3, 4, 5)
    assert result.total_payout == 0
    assert draw.status == DrawStatus.COMPLETED
    assert draw.executed_at == execution_time
    assert distribution.balance == 300
    assert jackpot.balance == 2_000
    assert generator.calls == 1


async def test_completed_draw_settlement_is_idempotent() -> None:
    now = datetime(2026, 8, 14, 17, tzinfo=UTC)
    _, _, draw, _, _, _ = build_purchase_accounts(now)
    draw.status = DrawStatus.COMPLETED
    draw.winning_numbers = [1, 2, 3, 4, 5]
    draw.total_payout = 123
    fake = FakeSession(scalar_values=[draw])
    generator = FixedGenerator()
    service = WeeklySettlementService(cast(AsyncSession, fake), generator)

    result = await service.settle(draw.id, now=now)

    assert result.already_completed
    assert result.total_payout == 123
    assert generator.calls == 0
    assert fake.added == []


async def test_settlement_enqueues_one_result_notification_per_user() -> None:
    now = datetime(2026, 8, 14, 17, tzinfo=UTC)
    execution_time = now + timedelta(hours=2)
    user_id, lottery, draw, balance, jackpot, distribution = build_purchase_accounts(
        now
    )
    ticket = Ticket(
        id=UUID(int=800),
        public_number=11,
        lottery_id=lottery.id,
        draw_id=draw.id,
        user_id=user_id,
        numbers=[6, 7, 8, 9, 10],
        purchase_price=100,
        prize_amount=0,
    )
    reserve = LotteryReserve(
        id=UUID(int=700), lottery_id=lottery.id, balance=1_000, version=1
    )
    fake = FakeSession(
        scalar_values=[draw, lottery, jackpot, distribution, reserve],
        scalar_collections=[[ticket], [balance], [user_id]],
    )

    await WeeklySettlementService(cast(AsyncSession, fake), FixedGenerator()).settle(
        draw.id, now=execution_time
    )

    notifications = [
        item for item in fake.added if isinstance(item, NotificationOutbox)
    ]
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.type == NotificationType.DRAW_RESULT
    assert notification.payload["total_prize"] == 0
    assert notification.payload["tickets"][0]["matches"] == 0


async def test_draw_cannot_be_settled_before_official_time() -> None:
    now = datetime(2026, 8, 14, 17, tzinfo=UTC)
    _, _, draw, _, _, _ = build_purchase_accounts(now)
    fake = FakeSession(scalar_values=[draw])
    generator = FixedGenerator()
    service = WeeklySettlementService(cast(AsyncSession, fake), generator)

    with pytest.raises(InvalidStateTransition):
        await service.settle(draw.id, now=now)

    assert generator.calls == 0
