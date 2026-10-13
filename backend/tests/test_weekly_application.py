"""Unit tests for Weekly transactional orchestration without a live database."""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.daily import DailySettlementService, DailyTicketPurchaseService
from k_loto.application.weekly import (
    LotterySettlementService,
    LotteryTicketPurchaseService,
    WeeklySettlementService,
    WeeklyTicketPurchaseService,
)
from k_loto.domain.enums import (
    DrawStatus,
    InAppNotificationType,
    LedgerAccountKind,
    LotteryKind,
    NotificationType,
    TicketSource,
    TransactionType,
)
from k_loto.domain.errors import InvalidStateTransition, InvalidTicket
from k_loto.infrastructure.database.models import (
    Balance,
    DistributionFund,
    Draw,
    JackpotAccount,
    JackpotWinEvent,
    KasperFundAccount,
    LedgerTransaction,
    Lottery,
    LotteryReserve,
    NotificationOutbox,
    Ticket,
    UserNotification,
    UserNotificationPreference,
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

    async def flush(self) -> None:
        return None


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


class FixedSeptemberGenerator:
    def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]:
        assert (population_size, numbers_to_pick) == (33, 3)
        return (1, 2, 3)


class FixedFastGenerator:
    def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]:
        assert (population_size, numbers_to_pick) == (15, 3)
        return (1, 2, 3)


class FixedFastPartialGenerator:
    def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]:
        assert (population_size, numbers_to_pick) == (15, 3)
        return (1, 2, 4)


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
    fake = FakeSession(scalar_values=[None, lottery, jackpot, None, draw, 0, balance])
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
    assert jackpot.balance == 2_200
    assert distribution.balance == 300
    assert lottery.next_ticket_number == 13
    assert draw.ticket_count == 2
    assert draw.total_sales == 200
    assert result.total_cost == 200
    assert len(ledger) == 2
    assert sum(item.amount for item in ledger) == 0
    notifications = [
        item for item in fake.added if isinstance(item, NotificationOutbox)
    ]
    assert notifications == []


async def test_september_purchase_credits_the_full_jackpot() -> None:
    now = datetime(2026, 9, 1, 12, tzinfo=UTC)
    user_id = UUID(int=920)
    lottery = Lottery(
        id=UUID(int=921),
        code="september",
        name="3 СЕНТЯБРЯ",
        kind=LotteryKind.DAILY,
        ruleset_code="september_3_33",
        numbers_to_pick=3,
        max_number=33,
        ticket_price=333,
        timezone="Europe/Moscow",
        schedule={"slots": ["03:33", "15:33"]},
        sales_cutoff_minutes=2,
        max_tickets_per_purchase=1000,
        max_tickets_per_user_per_draw=5000,
        is_active=True,
        next_draw_number=100,
        next_ticket_number=200,
    )
    draw = Draw(
        id=UUID(int=922),
        lottery_id=lottery.id,
        public_number=99,
        status=DrawStatus.SCHEDULED,
        scheduled_at=now + timedelta(hours=1),
        sales_close_at=now + timedelta(minutes=58),
        correlation_id=UUID(int=923),
        ticket_count=0,
        total_sales=0,
        total_payout=0,
        reserve_used=0,
    )
    balance = Balance(user_id=user_id, amount=1_000, version=1)
    jackpot = JackpotAccount(
        id=UUID(int=924),
        lottery_id=lottery.id,
        balance=33_333_333,
        base_amount=33_333_333,
        version=1,
    )
    distribution = DistributionFund(
        id=UUID(int=925), lottery_id=lottery.id, balance=0, version=1
    )
    fake = FakeSession(scalar_values=[None, lottery, jackpot, None, draw, 0, balance])

    result = await LotteryTicketPurchaseService(
        cast(AsyncSession, fake), lottery_code="september"
    ).purchase(
        user_id=user_id,
        combinations=[[3, 9, 33]],
        idempotency_key="september-purchase",
        now=now,
    )

    ledger = [item for item in fake.added if isinstance(item, LedgerTransaction)]
    assert result.total_cost == 333
    assert balance.amount == 667
    assert jackpot.balance == 33_333_666
    assert distribution.balance == 0
    assert [item.account_kind for item in ledger] == [
        LedgerAccountKind.USER_BALANCE,
        LedgerAccountKind.JACKPOT,
    ]
    assert sum(item.amount for item in ledger) == 0


async def test_five_draw_purchase_is_prepaid_and_created_atomically() -> None:
    now = datetime(2026, 8, 14, 17, tzinfo=UTC)
    user_id, lottery, draw, balance, jackpot, distribution = build_purchase_accounts(
        now
    )
    fake = FakeSession(
        scalar_values=[
            None,
            lottery,
            jackpot,
            None,
            draw,
            0,
            0,
            0,
            0,
            0,
            balance,
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
    assert jackpot.balance == 2_500
    assert distribution.balance == 300


async def test_daily_purchase_credits_full_jackpot_and_independent_numbering() -> None:
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
    fake = FakeSession(scalar_values=[None, lottery, jackpot, None, draw, 0, balance])

    result = await DailyTicketPurchaseService(cast(AsyncSession, fake)).purchase(
        user_id=user_id,
        combinations=[[1, 2, 3, 4], [1, 2, 3, 4]],
        idempotency_key="daily-checkout",
        now=now,
    )

    tickets = [item for item in fake.added if isinstance(item, Ticket)]
    assert [item.public_number for item in tickets] == [50, 51]
    assert jackpot.balance == 2_200
    assert distribution.balance == 300
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
        scalar_values=[lottery, draw, None, jackpot, lottery, draw, jackpot, reserve],
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
            jackpot,
            None,
            None,
            closing_draw,
            0,
            balance,
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
        scalar_values=[lottery, draw, None, jackpot, lottery, draw, jackpot, reserve],
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
    assert not any(isinstance(item, NotificationOutbox) for item in fake.added)


async def test_completed_draw_settlement_is_idempotent() -> None:
    now = datetime(2026, 8, 14, 17, tzinfo=UTC)
    _, lottery, draw, _, _, _ = build_purchase_accounts(now)
    draw.status = DrawStatus.COMPLETED
    draw.winning_numbers = [1, 2, 3, 4, 5]
    draw.total_payout = 123
    fake = FakeSession(scalar_values=[lottery, draw])
    generator = FixedGenerator()
    service = WeeklySettlementService(cast(AsyncSession, fake), generator)

    result = await service.settle(draw.id, now=now)

    assert result.already_completed
    assert result.total_payout == 123
    assert generator.calls == 0
    assert fake.added == []


async def test_ordinary_result_does_not_enqueue_telegram_notification() -> None:
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
    preference = UserNotificationPreference(
        user_id=user_id,
        telegram_enabled=True,
        draw_results_enabled=True,
        inactivity_reminders_enabled=True,
    )
    fake = FakeSession(
        scalar_values=[lottery, draw, None, jackpot, lottery, draw, jackpot, reserve],
        scalar_collections=[[ticket], [balance], [preference]],
    )

    await WeeklySettlementService(cast(AsyncSession, fake), FixedGenerator()).settle(
        draw.id, now=execution_time
    )

    notifications = [
        item for item in fake.added if isinstance(item, NotificationOutbox)
    ]
    assert notifications == []


@pytest.mark.parametrize(
    ("source", "generator", "notified"),
    (
        (TicketSource.MANUAL, FixedFastGenerator(), True),
        (TicketSource.AUTO_PLAY, FixedFastGenerator(), True),
        (TicketSource.MANUAL, FixedFastPartialGenerator(), False),
    ),
)
async def test_fast_only_notifies_for_jackpot(
    source: TicketSource,
    generator: FixedFastGenerator | FixedFastPartialGenerator,
    notified: bool,
) -> None:
    now = datetime(2026, 9, 1, 12, tzinfo=UTC)
    user_id = UUID(int=850)
    lottery = Lottery(
        id=UUID(int=851),
        code="flash",
        name="FLASH",
        kind=LotteryKind.DAILY,
        ruleset_code="fast_3_15",
        numbers_to_pick=3,
        max_number=15,
        ticket_price=888,
        timezone="Europe/Moscow",
        schedule={"type": "interval", "interval_minutes": 20},
        sales_cutoff_minutes=1,
        max_tickets_per_purchase=100,
        max_tickets_per_user_per_draw=500,
        is_active=True,
        next_draw_number=2,
        next_ticket_number=2,
    )
    draw = Draw(
        id=UUID(int=852),
        lottery_id=lottery.id,
        public_number=1,
        status=DrawStatus.SCHEDULED,
        scheduled_at=now,
        sales_close_at=now - timedelta(minutes=1),
        correlation_id=UUID(int=853),
        ticket_count=1,
        total_sales=888,
        total_payout=0,
        reserve_used=0,
    )
    ticket = Ticket(
        id=UUID(int=854),
        public_number=1,
        lottery_id=lottery.id,
        draw_id=draw.id,
        user_id=user_id,
        numbers=[1, 2, 3],
        purchase_price=888,
        prize_amount=0,
        source=source,
    )
    balance = Balance(user_id=user_id, amount=10_000, version=1)
    jackpot = JackpotAccount(
        id=UUID(int=855),
        lottery_id=lottery.id,
        balance=888_888,
        base_amount=888_888,
        version=1,
    )
    fund = KasperFundAccount(id=UUID(int=856), balance=10_000_000, version=1)
    preference = UserNotificationPreference(
        user_id=user_id,
        telegram_enabled=True,
        draw_results_enabled=True,
        inactivity_reminders_enabled=True,
    )
    fake = FakeSession(
        scalar_values=[lottery, draw, None, jackpot, lottery, draw, jackpot, fund],
        scalar_collections=[[ticket], [balance], [preference]],
    )

    await LotterySettlementService(cast(AsyncSession, fake), generator).settle(
        draw.id, now=now
    )

    telegram = [item for item in fake.added if isinstance(item, NotificationOutbox)]
    in_app = [item for item in fake.added if isinstance(item, UserNotification)]
    if notified:
        assert len(telegram) == 1
        assert telegram[0].type == NotificationType.JACKPOT_WIN
        assert telegram[0].payload["win_amount"] == 888_888
        assert len(in_app) == 1
        assert in_app[0].type == InAppNotificationType.WIN
        assert in_app[0].payload["lottery_code"] == "flash"
        assert (
            len([item for item in fake.added if isinstance(item, JackpotWinEvent)]) == 1
        )
    else:
        assert telegram == []
        assert in_app == []
        assert not any(isinstance(item, JackpotWinEvent) for item in fake.added)


async def test_draw_cannot_be_settled_before_official_time() -> None:
    now = datetime(2026, 8, 14, 17, tzinfo=UTC)
    _, lottery, draw, _, _, _ = build_purchase_accounts(now)
    fake = FakeSession(scalar_values=[lottery, draw])
    generator = FixedGenerator()
    service = WeeklySettlementService(cast(AsyncSession, fake), generator)

    with pytest.raises(InvalidStateTransition):
        await service.settle(draw.id, now=now)

    assert generator.calls == 0


async def test_september_main_prize_is_refilled_from_reserve() -> None:
    now = datetime(2026, 9, 1, 12, tzinfo=UTC)
    lottery = Lottery(
        id=UUID(int=900),
        code="september",
        name="3 СЕНТЯБРЯ",
        kind=LotteryKind.DAILY,
        ruleset_code="september_3_33",
        numbers_to_pick=3,
        max_number=33,
        ticket_price=333,
        timezone="Europe/Moscow",
        schedule={"slots": ["03:33", "15:33"]},
        sales_cutoff_minutes=2,
        max_tickets_per_purchase=1000,
        max_tickets_per_user_per_draw=5000,
        is_active=True,
        next_draw_number=900,
        next_ticket_number=900,
    )
    draw = Draw(
        id=UUID(int=901),
        lottery_id=lottery.id,
        public_number=899,
        status=DrawStatus.SCHEDULED,
        scheduled_at=now,
        sales_close_at=now - timedelta(minutes=2),
        correlation_id=UUID(int=902),
        ticket_count=1,
        total_sales=333,
        total_payout=0,
        reserve_used=0,
    )
    user_id = UUID(int=903)
    ticket = Ticket(
        id=UUID(int=904),
        public_number=899,
        lottery_id=lottery.id,
        draw_id=draw.id,
        user_id=user_id,
        numbers=[1, 2, 3],
        purchase_price=333,
        prize_amount=0,
    )
    balance = Balance(user_id=user_id, amount=1_000, version=1)
    jackpot = JackpotAccount(
        id=UUID(int=905),
        lottery_id=lottery.id,
        balance=33_333_333,
        base_amount=33_333_333,
        version=1,
    )
    distribution = DistributionFund(
        id=UUID(int=906), lottery_id=lottery.id, balance=333, version=1
    )
    reserve = KasperFundAccount(id=UUID(int=907), balance=1_000_000_000, version=1)
    fake = FakeSession(
        scalar_values=[lottery, draw, None, jackpot, lottery, draw, jackpot, reserve],
        scalar_collections=[[ticket], [balance], [], [user_id]],
    )

    result = await LotterySettlementService(
        cast(AsyncSession, fake), FixedSeptemberGenerator()
    ).settle(draw.id, now=now)

    ledger = [item for item in fake.added if isinstance(item, LedgerTransaction)]
    assert result.total_payout == 33_333_333
    assert balance.amount == 33_334_333
    assert jackpot.balance == 33_333_333
    assert distribution.balance == 333
    assert reserve.balance == 966_666_667
    assert draw.reserve_used == 0
    assert draw.kasper_fund_used == 33_333_333
    assert sum(item.amount for item in ledger) == 0
    assert len([item for item in fake.added if isinstance(item, JackpotWinEvent)]) == 1
    inbox = [item for item in fake.added if isinstance(item, UserNotification)]
    assert {item.type.value for item in inbox} == {"WIN", "JACKPOT_NEWS"}


async def test_duplicate_purchase_key_cannot_expose_another_players_receipt():
    from k_loto.domain.errors import InvalidTicket

    existing = LedgerTransaction(account_id=UUID(int=5))
    fake = FakeSession(scalar_values=[existing])
    with pytest.raises(InvalidTicket, match="another request"):
        await WeeklyTicketPurchaseService(cast(AsyncSession, fake)).purchase(
            user_id=UUID(int=6),
            combinations=[[1, 2, 3, 4, 5]],
            idempotency_key="another-users-key",
        )
    assert not fake.added
