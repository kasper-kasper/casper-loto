"""Mini rules and real transactional integration through the existing engine."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from k_loto.application.scheduler import DrawScheduleService
from k_loto.application.weekly import (
    KASPER_FUND_ID,
    LotterySettlementService,
    LotteryTicketPurchaseService,
    _ledger_entry,
)
from k_loto.domain.enums import LedgerAccountKind, LotteryKind, TransactionType
from k_loto.domain.errors import InsufficientReserve, InvalidTicket
from k_loto.domain.lotteries import DAILY_LOTTERY_CODES, PLAYABLE_LOTTERY_CODES
from k_loto.domain.lottery_rules import (
    CASPER_MINI_RULES,
    CLASSIC_ECONOMY_RULES,
    SettlementTicket,
    SystemRandomNumberGenerator,
    get_lottery_rules,
)
from k_loto.domain.schedules import next_draw_at, sales_close_at
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    JackpotAccount,
    KasperFundAccount,
    LedgerTransaction,
    Lottery,
    Ticket,
    User,
    UserNotification,
)
from test_achievements import entry, launch, metrics, quiet
from test_achievements import pg as pg

SCHEDULE = {"slots": ["10:30", "19:15"], "future_draw_count": 5}


def test_mini_identity_and_isolated_strategy():
    assert "mini" in PLAYABLE_LOTTERY_CODES & DAILY_LOTTERY_CODES
    assert get_lottery_rules("casper_mini_6_30") is CASPER_MINI_RULES
    assert CASPER_MINI_RULES.max_number == 30
    assert CLASSIC_ECONOMY_RULES.max_number == 36
    assert CLASSIC_ECONOMY_RULES.fixed_payouts[2] == 30_000


@pytest.mark.parametrize(
    "numbers",
    (
        [1, 2, 3, 4, 5],
        [1, 2, 3, 4, 5, 5],
        [0, 2, 3, 4, 5, 6],
        [1, 2, 3, 4, 5, 31],
        [True, 2, 3, 4, 5, 6],
        [1.0, 2, 3, 4, 5, 6],
    ),
)
def test_mini_rejects_invalid_combinations(numbers):
    with pytest.raises(InvalidTicket):
        CASPER_MINI_RULES.validate_combination(numbers)


def test_random_selection_and_per_ticket_allocation():
    generator = SystemRandomNumberGenerator()
    combinations = [
        CASPER_MINI_RULES.generate_combination(generator) for _ in range(100)
    ]
    assert all(len(set(c)) == 6 and min(c) >= 1 and max(c) <= 30 for c in combinations)
    quote = CASPER_MINI_RULES.quote_purchase(combinations, 10_000, 1_000_000)
    assert (quote.total_cost, quote.jackpot_contribution) == (1_000_000, 400_000)
    assert quote.distribution_contribution == 600_000


@pytest.mark.parametrize(
    "matches,amount",
    [(0, 0), (1, 0), (2, 10000), (3, 30000), (4, 140000), (5, 1000000), (6, 20004000)],
)
def test_single_prize_category_includes_ticket_cost(matches, amount):
    numbers = tuple(range(1, matches + 1)) + tuple(range(20, 26 - matches))
    plan = CASPER_MINI_RULES.calculate_settlement(
        [SettlementTicket(UUID(int=1), 1, UUID(int=2), numbers, 10_000)],
        [6, 5, 4, 3, 2, 1],
        distribution_balance=0,
        jackpot_balance=20_004_000,
        reserve_balance=30_000_000,
        base_jackpot=20_000_000,
    )
    assert plan.payouts[0].amount == amount
    assert plan.jackpot_closing == (20_000_000 if matches == 6 else 20_004_000)


def test_jackpot_split_remainder_and_reset_match_classic():
    tickets = [
        SettlementTicket(UUID(int=n), n, UUID(int=100 + n), (1, 2, 3, 4, 5, 6), 10_000)
        for n in (3, 1, 2)
    ]
    plan = CASPER_MINI_RULES.calculate_settlement(
        tickets,
        [1, 2, 3, 4, 5, 6],
        distribution_balance=0,
        jackpot_balance=20_000_002,
        reserve_balance=20_000_000,
        base_jackpot=20_000_000,
    )
    assert [p.amount for p in plan.payouts] == [6_666_668, 6_666_667, 6_666_667]
    assert sum(p.amount for p in plan.payouts) == 20_000_002
    assert plan.jackpot_reset_credit == plan.jackpot_closing == 20_000_000
    with pytest.raises(InsufficientReserve):
        CASPER_MINI_RULES.calculate_settlement(
            tickets,
            [1, 2, 3, 4, 5, 6],
            distribution_balance=0,
            jackpot_balance=20_000_002,
            reserve_balance=19_999_999,
            base_jackpot=20_000_000,
        )


def test_schedule_is_always_moscow_across_timezones_and_midnight():
    after = datetime(2026, 10, 21, 7, 30, tzinfo=UTC)
    for zone in (UTC, ZoneInfo("America/Los_Angeles"), ZoneInfo("Asia/Tokyo")):
        assert next_draw_at(
            LotteryKind.DAILY, after.astimezone(zone), SCHEDULE
        ) == datetime(2026, 10, 21, 16, 15, tzinfo=UTC)
    evening = datetime(2026, 10, 21, 16, 15, tzinfo=UTC)
    next_morning = next_draw_at(LotteryKind.DAILY, evening, SCHEDULE)
    assert next_morning == datetime(2026, 10, 22, 7, 30, tzinfo=UTC)
    assert sales_close_at(
        LotteryKind.DAILY, next_morning, 2, SCHEDULE
    ) == next_morning - timedelta(minutes=2)


async def prepare(pg):
    uid = uuid4()
    now = datetime.now(UTC)
    async with pg() as s, s.begin():
        lottery = await s.scalar(select(Lottery).where(Lottery.code == "mini"))
        assert lottery and lottery.ticket_price == 10_000
        assert lottery.max_tickets_per_purchase == 100
        assert lottery.max_tickets_per_user_per_draw == 500
        lid = lottery.id
        s.add(User(id=uid, display_name="Mini test player"))
        await s.flush()
        s.add(Balance(user_id=uid, amount=100_000_000, version=1))
        s.add(
            _ledger_entry(
                operation_id=uuid4(),
                idempotency_key=f"mini-test:{uid}",
                account_kind=LedgerAccountKind.USER_BALANCE,
                account_id=uid,
                transaction_type=TransactionType.SYSTEM_ADJUSTMENT,
                before=0,
                after=100_000_000,
                user_id=uid,
            )
        )
        fund = await s.get(KasperFundAccount, KASPER_FUND_ID, with_for_update=True)
        if fund is None:
            s.add(KasperFundAccount(id=KASPER_FUND_ID, balance=100_000_000, version=1))
            s.add(
                _ledger_entry(
                    operation_id=uuid4(),
                    idempotency_key="mini-test:fund",
                    account_kind=LedgerAccountKind.KASPER_FUND,
                    account_id=KASPER_FUND_ID,
                    transaction_type=TransactionType.SYSTEM_ADJUSTMENT,
                    before=0,
                    after=100_000_000,
                )
            )
    async with pg() as s:
        draw, _ = await DrawScheduleService(s).ensure_next_draw(lid, reference=now)
    return uid, lid, draw.id, now


async def purchase(pg, uid, count=1, *, draw_count=1, key=None, now=None):
    async with pg() as s:
        return await LotteryTicketPurchaseService(s, "mini").purchase(
            user_id=uid,
            combinations=[[1, 2, 3, 4, 5, 6]] * count,
            draw_count=draw_count,
            idempotency_key=key or str(uuid4()),
            now=now,
        )


async def test_pg_purchase_limit_numbering_jackpot_and_idempotency(pg):
    uid, lid, _, now = await prepare(pg)
    async with pg() as s:
        classic = await s.scalar(
            select(JackpotAccount.balance).join(Lottery).where(Lottery.code == "khan")
        )
    result = await purchase(pg, uid, 100, now=now, key="mini-repeat")
    retry = await purchase(pg, uid, 100, now=now, key="mini-repeat")
    assert retry.already_processed and retry.ticket_ids == result.ticket_ids
    with pytest.raises(InvalidTicket, match="at most"):
        await purchase(pg, uid, 101, now=now)
    async with pg() as s:
        assert (
            await s.scalar(
                select(JackpotAccount.balance).where(JackpotAccount.lottery_id == lid)
            )
            == 20_400_000
        )
        assert (await s.get(Balance, uid)).amount == 99_000_000
        assert (
            await s.scalar(
                select(func.count()).select_from(Ticket).where(Ticket.lottery_id == lid)
            )
            == 100
        )
        assert (
            await s.scalar(
                select(JackpotAccount.balance)
                .join(Lottery)
                .where(Lottery.code == "khan")
            )
            == classic
        )
        ledger = list(
            (
                await s.scalars(
                    select(LedgerTransaction).where(
                        LedgerTransaction.operation_id == result.operation_id
                    )
                )
            ).all()
        )
        assert sorted(t.amount for t in ledger) == [-1_000_000, 400_000]
        assert all(t.details["burned_cas"] == 600_000 for t in ledger)


async def test_pg_concurrent_purchases_cannot_exceed_player_limit(pg):
    uid, lid, _, now = await prepare(pg)
    for _ in range(4):
        await purchase(pg, uid, 100, now=now)
    results = await asyncio.gather(
        purchase(pg, uid, 100, now=now),
        purchase(pg, uid, 100, now=now),
        return_exceptions=True,
    )
    assert sum(isinstance(r, InvalidTicket) for r in results) == 1
    async with pg() as s:
        assert (
            await s.scalar(
                select(func.count()).select_from(Ticket).where(Ticket.lottery_id == lid)
            )
            == 500
        )
        assert (await s.get(Balance, uid)).amount == 95_000_000


async def test_pg_five_draw_purchase_and_total_purchase_limit(pg):
    uid, lid, _, now = await prepare(pg)
    with pytest.raises(InvalidTicket, match="across all draws"):
        await purchase(pg, uid, 21, draw_count=5, now=now)
    result = await purchase(pg, uid, 20, draw_count=5, now=now)
    assert len(result.draw_ids) == 5 and len(result.ticket_ids) == 100
    async with pg() as s:
        draws = list(
            (
                await s.scalars(
                    select(Draw)
                    .where(Draw.id.in_(result.draw_ids))
                    .order_by(Draw.scheduled_at)
                )
            ).all()
        )
        assert [d.ticket_count for d in draws] == [20] * 5
        assert [d.public_number for d in draws] == [1, 2, 3, 4, 5]
        assert (
            await s.scalar(
                select(JackpotAccount.balance).where(JackpotAccount.lottery_id == lid)
            )
            == 20_400_000
        )


class MiniGenerator:
    def draw(self, population_size, numbers_to_pick):
        assert (population_size, numbers_to_pick) == (30, 6)
        return (1, 2, 3, 4, 5, 6)


async def test_pg_settlement_notifications_and_game_achievement_exclusion(pg):
    uid, lid, did, now = await prepare(pg)
    await launch(pg, [entry(code="mini-exclusion", target=1)])
    result = await purchase(pg, uid, 1, now=now)
    async with pg() as s:
        draw = await s.get(Draw, did)
        executed = draw.scheduled_at
    async with pg() as s:
        settled = await LotterySettlementService(s, MiniGenerator()).settle(
            did, now=executed
        )
    async with pg() as s:
        repeated = await LotterySettlementService(s, MiniGenerator()).settle(
            did, now=executed
        )
    assert settled.total_payout == 20_004_000 and repeated.already_completed
    await quiet(pg)
    m = await metrics(pg, uid)
    for key in (
        "paid_tickets",
        "spent_tickets",
        "draw_participations",
        "winning_tickets",
        "jackpots",
        "spent_cas",
        "received_game_cas",
    ):
        assert m.get(key, 0) == 0, (key, m)
    async with pg() as s:
        assert (await s.get(Balance, uid)).amount == 119_994_000
        assert (
            await s.scalar(
                select(JackpotAccount.balance).where(JackpotAccount.lottery_id == lid)
            )
            == 20_000_000
        )
        assert (await s.get(Ticket, result.ticket_ids[0])).prize_amount == 20_004_000
        notices = list(
            (
                await s.scalars(
                    select(UserNotification).where(UserNotification.user_id == uid)
                )
            ).all()
        )
        assert any(n.payload.get("lottery_code") == "mini" for n in notices)
