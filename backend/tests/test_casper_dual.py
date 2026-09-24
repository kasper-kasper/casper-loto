"""Casper Dual's two-draw ticket, prize and cutoff regressions."""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.dual import settle_dual_draw
from k_loto.application.weekly import LotteryTicketPurchaseService
from k_loto.domain.dual import (
    DUAL_JACKPOT,
    dual_matches,
    dual_phase,
    dual_prize,
)
from k_loto.domain.enums import DrawStatus, LotteryKind, TicketStatus
from k_loto.domain.errors import InvalidTicket
from k_loto.domain.lottery_rules import DUAL_RULES
from k_loto.domain.schedules import next_draw_at, sales_close_at
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    JackpotAccount,
    KasperFundAccount,
    LedgerTransaction,
    Lottery,
    Ticket,
)


class FixedGenerator:
    def draw(self, population_size: int, count: int) -> tuple[int, ...]:
        assert (population_size, count) == (12, 2)
        return (3, 10)


class ScalarRows:
    def __init__(self, rows: Iterable[Any]) -> None:
        self.rows = list(rows)

    def all(self) -> list[Any]:
        return self.rows


class SettlementSession:
    def __init__(
        self,
        tickets: list[Any],
        first: Any,
        jackpot: Any,
        fund: Any,
        balances: list[Any] | None = None,
    ) -> None:
        self.tickets = tickets
        self.first = first
        self.jackpot = jackpot
        self.fund = fund
        self.added: list[Any] = []
        self.scalar_calls = 0
        self.scalar_collections = iter([tickets, balances or []])

    async def scalar(self, _statement: Any) -> Any:
        self.scalar_calls += 1
        return self.jackpot if self.scalar_calls == 1 else self.fund

    async def scalars(self, _statement: Any) -> ScalarRows:
        return ScalarRows(next(self.scalar_collections))

    async def get(self, _model: Any, _id: Any) -> Any:
        return self.first

    def add(self, item: Any) -> None:
        self.added.append(item)


class TransactionContext:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *_args: Any) -> None:
        return None


class PurchaseSession:
    def __init__(self, scalar_values: list[Any]) -> None:
        self.scalar_values = iter(scalar_values)
        self.added: list[Any] = []

    def begin(self) -> TransactionContext:
        return TransactionContext()

    async def scalar(self, _statement: Any) -> Any:
        return next(self.scalar_values)

    def add(self, item: Any) -> None:
        self.added.append(item)

    def add_all(self, items: Iterable[Any]) -> None:
        self.added.extend(items)


@pytest.mark.asyncio
async def test_purchase_creates_one_ticket_for_two_draws_and_one_debit() -> None:
    now = datetime(2026, 9, 24, 0, 10, tzinfo=UTC)
    lottery_id = uuid4()
    user_id = uuid4()
    first_at = datetime(2026, 9, 24, 4, 30, tzinfo=UTC)
    second_at = datetime(2026, 9, 24, 21, 30, tzinfo=UTC)
    lottery = Lottery(
        id=lottery_id,
        code="dual",
        name="Casper Dual",
        kind=LotteryKind.DAILY,
        ruleset_code=DUAL_RULES.code,
        numbers_to_pick=4,
        max_number=24,
        ticket_price=20_000,
        timezone="Europe/Moscow",
        schedule={"slots": ["00:30", "07:30"]},
        sales_cutoff_minutes=2,
        max_tickets_per_purchase=1000,
        max_tickets_per_user_per_draw=5000,
        is_active=True,
        next_draw_number=3,
        next_ticket_number=1,
    )

    def make_draw(number: int, scheduled_at: datetime) -> Draw:
        return Draw(
            id=uuid4(),
            lottery_id=lottery_id,
            public_number=number,
            status=DrawStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            sales_close_at=scheduled_at - timedelta(minutes=2),
            correlation_id=uuid4(),
            ticket_count=0,
            total_sales=0,
            total_payout=0,
            reserve_used=0,
            configuration_snapshot={"ruleset_code": DUAL_RULES.code},
        )

    first = make_draw(1, first_at)
    second = make_draw(2, second_at)
    jackpot = JackpotAccount(
        id=uuid4(),
        lottery_id=lottery_id,
        balance=DUAL_JACKPOT,
        base_amount=DUAL_JACKPOT,
        version=1,
    )
    fund = KasperFundAccount(id=uuid4(), balance=10_000_000, version=1)
    balance = Balance(user_id=user_id, amount=100_000, version=1)
    session = PurchaseSession(
        [None, lottery, jackpot, None, first, second, 0, 0, fund, balance]
    )
    result = await LotteryTicketPurchaseService(
        cast(AsyncSession, session), lottery_code="dual"
    ).purchase(
        user_id=user_id,
        combinations=[[3, 10, 15, 22]],
        idempotency_key="dual-purchase",
        now=now,
    )
    tickets = [item for item in session.added if isinstance(item, Ticket)]
    assert len(tickets) == 1
    assert tickets[0].draw_id == first.id
    assert tickets[0].second_draw_id == second.id
    assert tickets[0].numbers == [3, 10, 15, 22]
    assert result.draw_ids == (first.id, second.id)
    assert result.draw_count == 1
    assert result.total_cost == 20_000
    assert balance.amount == 80_000
    assert fund.balance == 10_020_000
    assert jackpot.balance == DUAL_JACKPOT
    assert first.ticket_count == second.ticket_count == 1
    assert first.total_sales == 20_000
    assert second.total_sales == 0


@pytest.mark.parametrize(
    ("night", "dawn", "expected"),
    [
        (0, 0, 0),
        (1, 0, 0),
        (0, 1, 0),
        (2, 0, 0),
        (0, 2, 0),
        (1, 1, 10_000),
        (2, 1, 100_000),
        (1, 2, 100_000),
        (2, 2, DUAL_JACKPOT),
    ],
)
def test_dual_prize_categories(night: int, dawn: int, expected: int) -> None:
    assert dual_prize(night, dawn) == expected


def test_dual_requires_two_numbers_per_field() -> None:
    assert DUAL_RULES.validate_purchase_combination([10, 3, 23, 17]) == (
        3,
        10,
        17,
        23,
    )
    with pytest.raises(InvalidTicket):
        DUAL_RULES.validate_purchase_combination([1, 2, 3, 14])
    assert dual_matches([3, 10, 15, 22], [3, 10], "NIGHT") == 2
    assert dual_matches([3, 10, 15, 22], [3, 10], "DAWN") == 2


@pytest.mark.parametrize("first_phase", ["NIGHT", "DAWN"])
def test_dual_schedule_and_two_minute_cutoff(first_phase: str) -> None:
    schedule = {"slots": ["00:30", "07:30"]}
    first = datetime(2026, 9, 24, 0 if first_phase == "NIGHT" else 7, 30)
    first = first.replace(tzinfo=UTC) - timedelta(hours=3)
    second = next_draw_at(LotteryKind.DAILY, first, schedule)
    assert dual_phase(first) == first_phase
    assert dual_phase(second) != first_phase
    assert sales_close_at(LotteryKind.DAILY, first, 2, schedule) == first - timedelta(
        minutes=2
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("first_phase", ["NIGHT", "DAWN"])
async def test_first_round_preserves_ticket_second_round_pays(
    first_phase: str,
) -> None:
    first_time = datetime(2026, 9, 23, 21, 30, tzinfo=UTC)
    if first_phase == "DAWN":
        first_time += timedelta(hours=7)
    second_time = next_draw_at(
        LotteryKind.DAILY, first_time, {"slots": ["00:30", "07:30"]}
    )
    lottery = SimpleNamespace(id=uuid4(), ruleset_code=DUAL_RULES.code)
    first = SimpleNamespace(
        id=uuid4(),
        status=DrawStatus.SCHEDULED,
        scheduled_at=first_time,
        configuration_snapshot={"ruleset_code": DUAL_RULES.code},
        public_number=1,
    )
    second = SimpleNamespace(
        id=uuid4(),
        status=DrawStatus.SCHEDULED,
        scheduled_at=second_time,
        configuration_snapshot={"ruleset_code": DUAL_RULES.code},
        public_number=2,
    )
    ticket = SimpleNamespace(
        id=uuid4(),
        lottery_id=lottery.id,
        draw_id=first.id,
        second_draw_id=second.id,
        public_number=1,
        user_id=uuid4(),
        numbers=[3, 10, 15, 22],
        status=TicketStatus.PURCHASED,
        dual_night_matches=None,
        dual_dawn_matches=None,
    )
    jackpot = SimpleNamespace(
        id=uuid4(), balance=DUAL_JACKPOT, base_amount=DUAL_JACKPOT, version=1
    )
    fund = SimpleNamespace(id=uuid4(), balance=10_000_000, version=1)
    first_session = SettlementSession([ticket], first, jackpot, fund)
    first_result = await settle_dual_draw(
        cast(AsyncSession, first_session),
        first,
        lottery,
        first_time,
        FixedGenerator(),
    )
    assert first_result.total_payout == 0
    assert first.status == DrawStatus.COMPLETED
    assert ticket.status == TicketStatus.PURCHASED
    assert (ticket.dual_night_matches is None) != (ticket.dual_dawn_matches is None)
    assert not first_session.added

    balance = SimpleNamespace(user_id=ticket.user_id, amount=0, version=1)
    second_session = SettlementSession([ticket], first, jackpot, fund, [balance])
    second_result = await settle_dual_draw(
        cast(AsyncSession, second_session),
        second,
        lottery,
        second_time,
        FixedGenerator(),
    )
    assert second_result.total_payout == DUAL_JACKPOT
    assert ticket.status == TicketStatus.SETTLED
    assert ticket.matches == 22
    assert ticket.prize_amount == DUAL_JACKPOT
    assert jackpot.balance == DUAL_JACKPOT
    assert fund.balance == 5_000_000
    assert second.status == DrawStatus.COMPLETED
    assert any(
        isinstance(item, LedgerTransaction)
        and item.idempotency_key.endswith(":jackpot:refill")
        for item in second_session.added
    )
