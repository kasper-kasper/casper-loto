"""Focused New Year rules and real shared-engine purchase/settlement checks."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from k_loto.application.scheduler import DrawScheduleService
from k_loto.application.weekly import (
    LotterySettlementService,
    LotteryTicketPurchaseService,
)
from k_loto.domain.enums import LotteryKind, TransactionType
from k_loto.domain.errors import ConfigurationError, InsufficientReserve, InvalidTicket
from k_loto.domain.lottery_rules import NEW_YEAR_2027_RULES as rules
from k_loto.domain.lottery_rules import SettlementTicket, SystemRandomNumberGenerator
from k_loto.domain.schedules import next_draw_at, sales_close_at
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    JackpotAccount,
    JackpotWinEvent,
    LedgerTransaction,
    Lottery,
    Ticket,
    UserNotification,
)
from k_loto.infrastructure.telegram_messages import _display_numbers
from test_achievements import pg as pg
from test_casper_mini import prepare as prepare_mini


def ticket(number, numbers):
    return SettlementTicket(
        UUID(int=number), number, UUID(int=100 + number), tuple(numbers), 10_000
    )


def settle(tickets, **kwargs):
    return rules.calculate_settlement(
        tickets,
        [1, 2, 3],
        distribution_balance=0,
        jackpot_balance=kwargs.pop("jackpot_balance", 0),
        base_jackpot=0,
        reserve_balance=kwargs.pop("reserve_balance", 10_000_000),
        **kwargs,
    )


@pytest.mark.parametrize(
    "numbers", ([1, 1, 2], [0, 2, 3], [1, 2, 13], [1, 2], [True, 2, 3])
)
def test_invalid_symbols(numbers):
    with pytest.raises(InvalidTicket):
        rules.validate_combination(numbers)


def test_unordered_symbols_and_no_progressive_allocation():
    assert rules.validate_combination([3, 1, 2]) == (1, 2, 3)
    generated = rules.generate_combination(SystemRandomNumberGenerator())
    assert len(set(generated)) == 3 and 1 <= min(generated) <= max(generated) <= 12
    quote = rules.quote_purchase([[3, 1, 2]] * 101, 10_000, 1_010_000)
    assert quote.total_cost == quote.distribution_contribution == 1_010_000
    assert quote.jackpot_contribution == 0


def test_each_ticket_gets_only_one_full_payout():
    plan = settle(
        [
            ticket(1, [4, 5, 6]),
            ticket(2, [1, 5, 6]),
            ticket(3, [1, 2, 6]),
            ticket(4, [3, 2, 1]),
        ]
    )
    assert [p.amount for p in plan.payouts] == [0, 5_000, 30_000, 1_000_000]
    assert plan.reserve_used == plan.total_payout == 1_035_000
    assert not plan.jackpot_won
    assert (
        plan.jackpot_opening == plan.jackpot_closing == plan.jackpot_reset_credit == 0
    )


def test_duplicate_winning_tickets_share_exact_million_by_public_number():
    plan = settle([ticket(n, [3, 1, 2]) for n in (3, 1, 2)])
    assert [p.amount for p in plan.payouts] == [333_334, 333_333, 333_333]
    assert plan.total_payout == 1_000_000
    # A previous draw with no full match cannot increase the next prize.
    assert settle([ticket(1, [4, 5, 6])]).total_payout == 0
    assert settle([ticket(1, [1, 2, 3])]).total_payout == 1_000_000


def test_insufficient_fund_and_nonzero_progressive_account_rejected():
    with pytest.raises(InsufficientReserve):
        settle([ticket(1, [1, 2, 3])], reserve_balance=999_999)
    with pytest.raises(ConfigurationError):
        settle([], jackpot_balance=1)


def test_moscow_schedule_and_symbol_notification():
    after = datetime(2026, 10, 21, 18, 15, tzinfo=UTC)
    schedule = {"slots": ["21:15"]}
    expected = datetime(2026, 10, 22, 18, 15, tzinfo=UTC)
    for zone in (UTC, ZoneInfo("America/Los_Angeles"), ZoneInfo("Asia/Tokyo")):
        assert (
            next_draw_at(LotteryKind.DAILY, after.astimezone(zone), schedule)
            == expected
        )
    assert sales_close_at(LotteryKind.DAILY, expected, 2) == expected - timedelta(
        minutes=2
    )
    assert (
        _display_numbers([1, 4, 12], "newyear2027") == "Мандарины · Часы · Колокольчик"
    )


async def prepare(pg):
    # Reuse only the existing synthetic wallet/fund fixture; all New Year work
    # below runs through the same services as every ordinary lottery.
    uid, _, _, now = await prepare_mini(pg)
    async with pg() as s:
        lottery = await s.scalar(select(Lottery).where(Lottery.code == "newyear2027"))
        assert lottery.ticket_price == 10_000
        assert lottery.max_tickets_per_user_per_draw == 101
        lid = lottery.id
    async with pg() as s:
        draw, _ = await DrawScheduleService(s).ensure_next_draw(lid, reference=now)
    return uid, lid, draw.id, now


async def purchase(pg, uid, count, *, key=None, now=None):
    async with pg() as s:
        return await LotteryTicketPurchaseService(s, "newyear2027").purchase(
            user_id=uid,
            combinations=[[1, 2, 3]] * count,
            idempotency_key=key or str(uuid4()),
            now=now,
        )


async def test_pg_split_and_concurrent_purchases_cannot_bypass_101(pg):
    uid, lid, _, now = await prepare(pg)
    result = await purchase(pg, uid, 100, key="ny-retry", now=now)
    retry = await purchase(pg, uid, 100, key="ny-retry", now=now)
    assert retry.already_processed and retry.ticket_ids == result.ticket_ids
    answers = await asyncio.gather(
        purchase(pg, uid, 1, now=now),
        purchase(pg, uid, 1, now=now),
        return_exceptions=True,
    )
    assert sum(isinstance(answer, InvalidTicket) for answer in answers) == 1
    with pytest.raises(InvalidTicket):
        await purchase(pg, uid, 102, now=now)
    async with pg() as s:
        assert (
            await s.scalar(
                select(func.count()).select_from(Ticket).where(Ticket.lottery_id == lid)
            )
            == 101
        )
        assert (await s.get(Balance, uid)).amount == 98_990_000
        assert (
            await s.scalar(
                select(JackpotAccount.balance).where(JackpotAccount.lottery_id == lid)
            )
            == 0
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
        assert len(ledger) == 1 and ledger[0].amount == -1_000_000
        assert ledger[0].details["burned_cas"] == 1_000_000


class Generator:
    def draw(self, population_size, numbers_to_pick):
        assert (population_size, numbers_to_pick) == (12, 3)
        return (1, 2, 3)


async def test_pg_shared_settlement_is_ledgered_idempotent_and_has_no_jackpot_news(pg):
    uid, lid, did, now = await prepare(pg)
    result = await purchase(pg, uid, 3, now=now)
    async with pg() as s:
        when = (await s.get(Draw, did)).scheduled_at
    for _ in range(2):
        async with pg() as s:
            settled = await LotterySettlementService(s, Generator()).settle(
                did, now=when
            )
        assert settled.total_payout == 1_000_000
    assert settled.already_completed
    async with pg() as s:
        sold = list(
            (
                await s.scalars(
                    select(Ticket)
                    .where(Ticket.id.in_(result.ticket_ids))
                    .order_by(Ticket.public_number)
                )
            ).all()
        )
        assert [t.prize_amount for t in sold] == [333_334, 333_333, 333_333]
        entries = list(
            (
                await s.scalars(
                    select(LedgerTransaction).where(
                        LedgerTransaction.draw_id == did,
                        LedgerTransaction.type == TransactionType.PRIZE_PAYOUT,
                    )
                )
            ).all()
        )
        assert sum(t.amount for t in entries) == 0 and len(entries) == 4
        assert (
            await s.scalar(
                select(func.count())
                .select_from(JackpotWinEvent)
                .where(JackpotWinEvent.lottery_id == lid)
            )
            == 0
        )
        notices = list(
            (
                await s.scalars(
                    select(UserNotification).where(UserNotification.user_id == uid)
                )
            ).all()
        )
        assert any(n.payload.get("lottery_code") == "newyear2027" for n in notices)


async def test_pg_admin_cannot_turn_fixed_pool_into_progressive_jackpot(pg):
    from k_loto.application.admin import AdminMutationService
    from k_loto.application.distribution import validate_assignment

    uid, lid, did, now = await prepare(pg)
    async with pg() as s:
        with pytest.raises(ValueError, match="no progressive jackpot"):
            await AdminMutationService(s, uid).set_jackpot(
                lid,
                target_amount=1,
                reason="Synthetic guard test",
                idempotency_key="ny-no-jackpot",
            )
    async with pg() as s:
        with pytest.raises(ValueError, match="no progressive jackpot"):
            await AdminMutationService(s, uid).configure_lottery(
                lid,
                ticket_price=10_000,
                base_jackpot=1,
                reason="Synthetic guard test",
            )
    async with pg() as s:
        lottery, draw = await s.get(Lottery, lid), await s.get(Draw, did)
        with pytest.raises(ValueError):
            validate_assignment(draw, lottery, now)
        account = await s.scalar(
            select(JackpotAccount).where(JackpotAccount.lottery_id == lid)
        )
        assert account.balance == account.base_amount == 0
