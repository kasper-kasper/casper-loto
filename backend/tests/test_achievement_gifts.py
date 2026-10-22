"""Real PostgreSQL conservation, once-only gifts, deferral and paid eligibility."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from k_loto.application.achievements import (
    drain,
    execute_rewards,
    record_activity,
)
from k_loto.application.weekly import (
    KASPER_FUND_ID,
    LotterySettlementService,
    LotteryTicketPurchaseService,
)
from k_loto.domain.enums import TicketSource, TicketStatus
from k_loto.domain.errors import InvalidTicket
from k_loto.domain.lottery_rules import SEPTEMBER_ECONOMY_RULES
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementReward,
)
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    JackpotAccount,
    KasperFundAccount,
    LedgerTransaction,
    Lottery,
    Ticket,
)
from test_achievements import entry, launch, metrics, quiet, seed, tickets
from test_achievements import pg as pg


async def gift_draw(factory, *, cap=100):
    now = datetime.now(UTC)
    async with factory() as session, session.begin():
        lottery = await session.scalar(
            select(Lottery).where(Lottery.code == "september")
        )
        lottery.ruleset_code = SEPTEMBER_ECONOMY_RULES.code
        lottery.numbers_to_pick = SEPTEMBER_ECONOMY_RULES.numbers_to_pick
        lottery.max_number = SEPTEMBER_ECONOMY_RULES.max_number
        lottery.ticket_price = 3333
        lottery.is_active = True
        lottery.max_tickets_per_purchase = 1
        lottery.max_tickets_per_user_per_draw = cap
        draw = Draw(
            id=uuid4(),
            lottery_id=lottery.id,
            public_number=1,
            scheduled_at=now + timedelta(days=1),
            sales_close_at=now + timedelta(hours=23),
            configuration_snapshot={
                "ruleset_code": lottery.ruleset_code,
                "ticket_price": 3333,
            },
        )
        session.add(draw)
        return lottery.id, draw.id, draw.scheduled_at


@pytest.mark.asyncio
async def test_funded_cash_ticket_case_conservation_and_concurrent_replay(pg):
    uid, lid, did = await seed(pg)
    gift_lottery, gift_id, scheduled = await gift_draw(pg)
    rewards = [
        {"type": "cas", "amount": 20_000},
        {"type": "ticket", "amount": 1, "lottery": "september"},
        {"type": "case", "amount": 1, "planned": True},
    ]
    await launch(pg, [entry(target=1, rewards=rewards)])
    async with pg() as s:
        fund_before = (await s.get(KasperFundAccount, KASPER_FUND_ID)).balance
        jackpot_before = await s.scalar(
            select(JackpotAccount.balance).where(
                JackpotAccount.lottery_id == gift_lottery
            )
        )
    await tickets(pg, uid, lid, did, 1)
    await asyncio.gather(*(drain(pg, limit=30) for _ in range(4)))
    await quiet(pg)
    async with pg() as s:
        award = await s.scalar(select(AchievementAward))
        assert award.reward_status == "planned"
        gift = await s.scalar(select(Ticket).where(Ticket.source == TicketSource.GIFT))
        assert gift.draw_id == gift_id and gift.purchase_price == 0
        assert (
            gift.selection_mode == "random" and gift.achievement_reward_id is not None
        )
        assert len(gift.numbers) == len(set(gift.numbers)) == 3
        assert (await s.get(Balance, uid)).amount == 1_020_000
        assert (
            await s.get(KasperFundAccount, KASPER_FUND_ID)
        ).balance == fund_before - 23_333
        assert (
            await s.scalar(
                select(JackpotAccount.balance).where(
                    JackpotAccount.lottery_id == gift_lottery
                )
            )
            == jackpot_before + 1667
        )
        case = await s.scalar(
            select(AchievementReward).where(AchievementReward.status == "planned")
        )
        assert case.completed_at is None and case.retry_at is None
        ledger = list(
            await s.scalars(
                select(LedgerTransaction).where(LedgerTransaction.user_id == uid)
            )
        )
        assert sum(row.amount for row in ledger) == -1666
        assert (
            sum(
                row.details.get("burned_cas", 0)
                for row in ledger
                if row.account_id == KASPER_FUND_ID and row.type == "TICKET_PURCHASE"
            )
            == 1666
        )
        award_id, gift_numbers = award.id, gift.numbers
    assert (await metrics(pg, uid))["paid_tickets"] == 1
    assert (await metrics(pg, uid))["gift_tickets"] == 1

    async def replay():
        async with pg() as s, s.begin():
            await execute_rewards(s, award_id, datetime.now(UTC))

    await asyncio.gather(*(replay() for _ in range(4)))
    async with pg() as s:
        assert (
            await s.scalar(
                select(func.count())
                .select_from(Ticket)
                .where(Ticket.source == TicketSource.GIFT)
            )
            == 1
        )

    class ExactWinning:
        def draw(self, maximum, count):
            return tuple(gift_numbers)

    async with pg() as s:
        await LotterySettlementService(s, number_generator=ExactWinning()).settle(
            gift_id, now=scheduled + timedelta(seconds=1)
        )
    await quiet(pg)
    async with pg() as s:
        settled = await s.get(Ticket, gift.id)
        assert settled.status == TicketStatus.SETTLED and settled.prize_amount > 0
        assert (await s.get(Balance, uid)).amount > 1_020_000
    assert not (await metrics(pg, uid)).get("winning_tickets")


@pytest.mark.asyncio
async def test_waiting_gift_does_not_block_cash_activity_or_case_and_later_recovers(pg):
    uid, lid, did = await seed(pg)
    await launch(
        pg,
        [
            entry(
                target=1,
                rewards=[
                    {"type": "cas", "amount": 20_000},
                    {"type": "ticket", "amount": 1, "lottery": "september"},
                    {"type": "case", "amount": 1, "planned": True},
                ],
            )
        ],
    )
    await tickets(pg, uid, lid, did, 1)
    await quiet(pg)
    async with pg() as s, s.begin():
        assert (await s.get(Balance, uid)).amount == 1_020_000
        part = await s.scalar(
            select(AchievementReward).where(AchievementReward.status == "waiting")
        )
        assert part is not None and part.completed_at is None
        await record_activity(s, uid, datetime.now(UTC))
    await quiet(pg)
    assert (await metrics(pg, uid))["active_days"] == 1
    await gift_draw(pg)
    async with pg() as s, s.begin():
        await s.execute(
            update(AchievementReward)
            .where(AchievementReward.status == "waiting")
            .values(retry_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    await quiet(pg)
    async with pg() as s:
        assert (
            await s.scalar(
                select(func.count())
                .select_from(Ticket)
                .where(Ticket.source == TicketSource.GIFT)
            )
            == 1
        )
        assert (await s.scalar(select(AchievementAward))).reward_status == "planned"


@pytest.mark.asyncio
async def test_insufficient_fund_preserves_reward_without_issuing_cas(pg):
    uid, lid, did = await seed(pg)
    async with pg() as s, s.begin():
        # Synthetic sandbox fixture, no real fund or player history.
        (await s.get(KasperFundAccount, KASPER_FUND_ID)).balance = 1
    await launch(pg, [entry(target=1, rewards=[{"type": "cas", "amount": 20_000}])])
    await tickets(pg, uid, lid, did, 1)
    await quiet(pg)
    async with pg() as s:
        assert (await s.get(Balance, uid)).amount == 1_000_000
        assert (await s.scalar(select(AchievementAward))).reward_status == "waiting"
        assert (
            await s.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(LedgerTransaction.type == "ACHIEVEMENT_REWARD")
            )
            == 0
        )


@pytest.mark.asyncio
async def test_client_cannot_request_unbacked_gift_ticket(pg):
    uid, _, _ = await seed(pg)
    async with pg() as s:
        with pytest.raises(InvalidTicket, match="server reward"):
            await LotteryTicketPurchaseService(s, lottery_code="september").purchase(
                user_id=uid,
                combinations=[[1, 2, 3]],
                idempotency_key="forged-gift",
                source=TicketSource.GIFT,
            )
