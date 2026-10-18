"""Approved Dual/Bingo payouts, inclusive cutoffs and safe card retirement."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from k_loto.application.bingo import (
    _STAGE_CACHE,
    BingoQueryService,
    delete_unused_cards,
)
from k_loto.application.dual_bingo_economy import (
    BingoEconomyService,
    DualEconomyService,
)
from k_loto.application.weekly import LotterySettlementService
from k_loto.domain.bingo import BINGO_ECONOMY_CODE, outcomes
from k_loto.domain.distribution import distribute_jackpot
from k_loto.domain.dual import DUAL_ECONOMY_CODE, dual_prize
from k_loto.domain.enums import DrawStatus, LotteryKind, TicketStatus
from k_loto.domain.errors import InsufficientReserve, InvalidStateTransition
from k_loto.domain.lottery_rules import BINGO_ECONOMY_RULES, SettlementTicket
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    Balance,
    Draw,
    JackpotAccount,
    KasperFundAccount,
    LedgerTransaction,
    Lottery,
    Ticket,
)
from test_themed_economy import BatchSession, batch_objects
from test_weekly_application import FakeSession


def test_bingo_api_allows_75_cards_but_rejects_76():
    from pydantic import ValidationError

    from k_loto.api.routes.miniapp import BingoPurchaseRequest

    assert (
        BingoPurchaseRequest(
            draw_id=uuid4(), quantity=75, idempotency_key="all"
        ).quantity
        == 75
    )
    with pytest.raises(ValidationError):
        BingoPurchaseRequest(draw_id=uuid4(), quantity=76, idempotency_key="over")


@pytest.mark.parametrize(
    "night,dawn,amount",
    [
        (0, 2, 0),
        (2, 0, 0),
        (1, 1, 300_000),
        (1, 2, 1_000_000),
        (2, 1, 1_000_000),
        (2, 2, 10_000_000),
    ],
)
def test_dual_new_fixed_categories(night, dawn, amount):
    assert dual_prize(night, dawn, ruleset_code=DUAL_ECONOMY_CODE) == amount


@pytest.mark.parametrize(
    "numbers,expected",
    [
        ((1, 2, 3, 18, 20, 21, 22, 34, 40, 41, 42, 58), (50_000, 100_000, 0, 20_000)),
        ((1, 2, 3, 19, 20, 21, 22, 35, 40, 41, 42, 59), (0, 0, 0, 0)),
        ((1, 2, 3, 18, 20, 21, 22, 35, 40, 41, 42, 58), (50_000, 0, 0, 20_000)),
        ((1, 2, 3, 19, 20, 21, 22, 34, 40, 41, 42, 59), (0, 100_000, 0, 0)),
    ],
)
def test_bingo_inclusive_cutoffs_and_independent_stacking(numbers, expected):
    tid = uuid4()
    result = outcomes(
        [(tid, 1, numbers)], tuple(range(1, 59)), 1_000_000_000, fixed_per_card=True
    )
    assert result[tid].amounts == expected
    assert BINGO_ECONOMY_RULES.validate_combination(numbers) == numbers


def test_fixed_prizes_are_not_shared_and_jackpot_uses_integer_remainders():
    tickets = [(UUID(int=i), i, tuple(range(1, 13))) for i in (3, 2, 1)]
    results = outcomes(tickets, tuple(range(1, 59)), 1_000_000_001, fixed_per_card=True)
    assert all(
        (r.amounts[0], r.amounts[1], r.amounts[3]) == (50_000, 100_000, 20_000)
        for r in results.values()
    )
    assert sum(r.amounts[2] for r in results.values()) == 1_000_000_001
    assert results[UUID(int=1)].amounts[2] == 333_333_334
    # Historical payouts still use the original pools and three-slot format.
    old = outcomes(tickets, tuple(range(1, 59)), 1_000_000_001)
    assert sum(r.amounts[0] for r in old.values()) == 100_000
    assert all(len(r.amounts) == 3 for r in old.values())


@pytest.mark.parametrize("last,jackpot", [(28, 1_000_020_000), (29, 0)])
def test_bingo_fund_covers_all_fixed_prizes_and_jackpot_reset(last, jackpot):
    ticket = SettlementTicket(uuid4(), 1, uuid4(), (*range(1, 12), last), 50_000)
    params = dict(
        distribution_balance=0,
        jackpot_balance=1_000_020_000,
        reserve_balance=2_000_000_000,
        base_jackpot=1_000_000_000,
    )
    plan = BINGO_ECONOMY_RULES.calculate_settlement(
        [ticket], tuple(range(1, 59)), **params
    )
    assert plan.total_payout == 170_000 + jackpot
    assert plan.reserve_used == 170_000 + (1_000_000_000 if jackpot else 0)
    assert plan.payouts[0].jackpot_amount == jackpot
    assert BINGO_ECONOMY_RULES.jackpot_contribution(50_000) == 20_000
    with pytest.raises(InsufficientReserve):
        BINGO_ECONOMY_RULES.calculate_settlement(
            [ticket],
            tuple(range(1, 59)),
            **{**params, "reserve_balance": plan.reserve_used - 1},
        )
    if not jackpot:
        rolled = distribute_jackpot(
            plan,
            [ticket],
            BINGO_ECONOMY_RULES,
            base_jackpot=1_000_000_000,
            fund_balance=params["reserve_balance"],
        )
        assert rolled.distribution_category == "bingo-tour-2"
        assert rolled.total_payout == 170_000 + params["jackpot_balance"]


@pytest.mark.parametrize(
    "service,cap", [(DualEconomyService, 50), (BingoEconomyService, 75)]
)
async def test_paused_batch_preserves_counters_and_applies_once(service, cap):
    control, lotteries, jackpots, fund = batch_objects(service.terms)
    before = [(x.next_draw_number, x.next_ticket_number) for x in lotteries]
    fake = BatchSession(
        scalar_values=[object(), control, None, None, fund],
        scalar_collections=[lotteries, jackpots],
    )
    owner = uuid4()
    await service(cast(AsyncSession, fake)).apply(owner_id=owner)
    lottery, jackpot = lotteries[0], jackpots[0]
    _, rule, price, base = service.terms[0]
    assert (lottery.ruleset_code, lottery.ticket_price) == (rule.code, price)
    assert lottery.max_tickets_per_user_per_draw == cap
    assert lottery.max_tickets_per_purchase == cap
    assert (jackpot.balance, jackpot.base_amount) == (base, base)
    assert before == [(x.next_draw_number, x.next_ticket_number) for x in lotteries]
    ledger = [x for x in fake.added if isinstance(x, LedgerTransaction)]
    assert len(ledger) == 2 and sum(x.amount for x in ledger) == 0
    audit = next(x for x in fake.added if isinstance(x, AdminAuditLog))
    assert audit.new_values["burned_cas"] == (
        0 if service is DualEconomyService else 30_000
    )
    assert control.paused and control.epoch == 2 and control.recovery_after is None
    repeat = BatchSession(scalar_values=[object(), control])
    assert (await service(cast(AsyncSession, repeat)).apply(owner_id=owner))[
        "already_applied"
    ]
    assert not repeat.added


async def test_cleanup_deletes_only_unsold_cards_for_completed_draw_and_rolls_back():
    engine = create_engine("sqlite://")
    target = Draw(id=UUID(int=1), status=DrawStatus.COMPLETED)
    with Session(engine) as session:
        session.execute(
            text(
                "CREATE TABLE bingo_pool_tickets(id INTEGER, draw_id CHAR(32), "
                "ticket_id CHAR(32))"
            )
        )
        for index, draw, ticket in (
            (1, UUID(int=1), None),
            (2, UUID(int=1), UUID(int=2).hex),
            (3, UUID(int=2), None),
        ):
            session.execute(
                text("INSERT INTO bingo_pool_tickets VALUES (:id,:draw,:ticket)"),
                dict(id=index, draw=draw.hex, ticket=ticket),
            )
        session.commit()

        class Adapter:
            async def execute(self, statement):
                return session.execute(statement)

        adapter = cast(AsyncSession, Adapter())
        with pytest.raises(RuntimeError, match="rollback"):
            with session.begin():
                await delete_unused_cards(adapter, target)
                raise RuntimeError("rollback")
        assert session.scalar(text("SELECT COUNT(*) FROM bingo_pool_tickets")) == 3
        await delete_unused_cards(adapter, target)
        await delete_unused_cards(adapter, target)
        assert list(
            session.scalars(text("SELECT id FROM bingo_pool_tickets ORDER BY id"))
        ) == [2, 3]
        with pytest.raises(InvalidStateTransition):
            await delete_unused_cards(
                adapter, Draw(id=UUID(int=2), status=DrawStatus.DRAWING)
            )
    engine.dispose()


@pytest.mark.parametrize("revealed", [57, 58])
async def test_feed_third_tour_is_revealed_at_move_58_and_keeps_all_75_cards(
    revealed, monkeypatch
):
    now = datetime(2026, 10, 18, tzinfo=UTC)

    class Clock:
        @staticmethod
        def now(_tz):
            return now

    monkeypatch.setattr("k_loto.application.bingo.datetime", Clock)
    from datetime import timedelta

    draw = Draw(
        id=uuid4(),
        configuration_snapshot={"ruleset_code": BINGO_ECONOMY_CODE},
        status=DrawStatus.DRAWING,
        winning_numbers=list(range(1, 59)),
        executed_at=now - timedelta(seconds=2 * revealed),
        scheduled_at=now,
        public_number=1,
    )
    cards = [
        SimpleNamespace(
            id=uuid4(),
            public_number=i,
            numbers=[*range(1, 12), 58],
            purchase_price=50_000,
        )
        for i in range(75)
    ]
    fake = FakeSession(
        scalar_values=[draw, SimpleNamespace(ruleset_code=BINGO_ECONOMY_CODE)],
        scalar_collections=[cards, cards],
    )
    _STAGE_CACHE.clear()
    feed = await BingoQueryService(cast(AsyncSession, fake)).feed(uuid4())
    assert feed["rules"]["tour_prizes"] == [50_000, 100_000, 20_000]
    assert len(feed["draw"]["tickets"]) == 75
    assert len(feed["draw"]["numbers"]) == revealed
    assert feed["draw"]["stages"][3] == {
        "move": 58 if revealed == 58 else None,
        "winners": 75 if revealed == 58 else 0,
    }


@pytest.mark.parametrize("fund_balance", [2_000_000_000, 169_999])
async def test_bingo_third_tour_is_ledgered_once_and_cleanup_waits_for_success(
    fund_balance,
):
    from datetime import timedelta

    now = datetime(2026, 10, 18, tzinfo=UTC)
    lottery = Lottery(
        id=uuid4(),
        code="bingo",
        name="Casper Bingo",
        kind=LotteryKind.DAILY,
        ruleset_code=BINGO_ECONOMY_CODE,
        numbers_to_pick=12,
        max_number=60,
    )
    draw = Draw(
        id=uuid4(),
        lottery_id=lottery.id,
        public_number=7,
        status=DrawStatus.DRAWING,
        scheduled_at=now - timedelta(minutes=3),
        executed_at=now - timedelta(minutes=3),
        winning_numbers=list(range(1, 59)),
        jackpot_opening=1_000_020_000,
        configuration_snapshot={
            "ruleset_code": BINGO_ECONOMY_CODE,
            "base_jackpot": 1_000_000_000,
        },
    )
    ticket = Ticket(
        id=uuid4(),
        draw_id=draw.id,
        user_id=uuid4(),
        public_number=99,
        numbers=[*range(1, 12), 58],
        purchase_price=50_000,
        status=TicketStatus.PURCHASED,
    )
    balance = Balance(user_id=ticket.user_id, amount=0, version=1)
    jackpot = JackpotAccount(
        id=uuid4(), balance=1_000_020_000, base_amount=1_000_000_000, version=1
    )
    fund = KasperFundAccount(id=uuid4(), balance=fund_balance, version=1)
    fake = FakeSession(
        scalar_values=[lottery, draw, None, lottery, draw, jackpot, fund],
        scalar_collections=[[ticket], [balance], []],
    )
    fake.execute = AsyncMock()
    service = LotterySettlementService(cast(AsyncSession, fake))
    if fund_balance < 170_000:
        with pytest.raises(InsufficientReserve):
            await service.settle(draw.id, now=now)
        fake.execute.assert_not_awaited()
        assert ticket.status == TicketStatus.PURCHASED and not fake.added
        return
    await service.settle(draw.id, now=now)
    assert draw.status == DrawStatus.COMPLETED
    assert ticket.bingo_result["amounts"] == [50_000, 100_000, 0, 20_000]
    assert balance.amount == draw.total_payout == ticket.prize_amount == 170_000
    assert fund.balance == fund_balance - 170_000 and jackpot.balance == 1_000_020_000
    ledger = [x for x in fake.added if isinstance(x, LedgerTransaction)]
    assert len(ledger) == 2 and sum(x.amount for x in ledger) == 0
    fake.execute.assert_awaited_once()
    retry = FakeSession(scalar_values=[lottery, draw])
    assert (
        await LotterySettlementService(cast(AsyncSession, retry)).settle(
            draw.id, now=now
        )
    ).already_completed
    assert not retry.added and balance.amount == 170_000
