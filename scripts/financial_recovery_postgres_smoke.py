"""Financial regressions on an empty, disposable audit database only."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError

from k_loto.application.admin import AdminMutationService
from k_loto.application.instant import InstantTicketPurchaseService
from k_loto.application.purchase_receipts import PurchaseReceiptService
from k_loto.application.weekly import (
    KASPER_FUND_ID,
    LotterySettlementService,
    LotteryTicketPurchaseService,
)
from k_loto.core.config import get_settings
from k_loto.domain import bingo
from k_loto.domain.enums import DrawStatus, LedgerAccountKind, LotteryKind, TicketStatus
from k_loto.domain.errors import ConfigurationError, InsufficientReserve, InvalidTicket
from k_loto.infrastructure.database.models import (
    Balance,
    BingoPoolTicket,
    Draw,
    JackpotAccount,
    KasperFundAccount,
    LedgerTransaction,
    Lottery,
    Ticket,
    User,
)
from k_loto.infrastructure.database.session import engine, session_factory
from scripts.postgres_e2e_smoke import ledger_credit


class FixedNumbers:
    def __init__(self):
        self.calls = 0

    def draw(self, population_size, numbers_to_pick):
        self.calls += 1
        assert (population_size, numbers_to_pick) == (20, 5)
        return (1, 2, 3, 4, 5)


async def seed(now):
    user = uuid4()
    async with session_factory() as session, session.begin():
        session.add(User(id=user, display_name="Isolated financial smoke"))
        await session.flush()
        session.add(Balance(user_id=user, amount=10_000_000))
        session.add(
            ledger_credit(
                account_kind=LedgerAccountKind.USER_BALANCE,
                account_id=user,
                amount=10_000_000,
                user_id=user,
            )
        )
        session.add(KasperFundAccount(id=KASPER_FUND_ID, balance=0))
        lottery = Lottery(
            id=uuid4(),
            code="audit-weekly",
            name="Audit Weekly",
            kind=LotteryKind.WEEKLY,
            ruleset_code="weekly_5_20",
            numbers_to_pick=5,
            max_number=20,
            ticket_price=100,
            sales_cutoff_minutes=5,
            schedule={},
            is_active=True,
            next_draw_number=2,
            next_ticket_number=1,
        )
        session.add(lottery)
        await session.flush()
        draw = Draw(
            id=uuid4(),
            lottery_id=lottery.id,
            public_number=1,
            status=DrawStatus.SCHEDULED,
            scheduled_at=now + timedelta(hours=1),
            sales_close_at=now + timedelta(minutes=55),
            correlation_id=uuid4(),
            configuration_snapshot={
                "ruleset_code": "weekly_5_20",
                "base_jackpot": 1000,
            },
        )
        jackpot = JackpotAccount(
            id=uuid4(),
            lottery_id=lottery.id,
            balance=2000,
            base_amount=1000,
        )
        session.add_all([draw, jackpot])
        session.add(
            ledger_credit(
                account_kind=LedgerAccountKind.JACKPOT,
                account_id=jackpot.id,
                amount=2000,
                lottery_id=lottery.id,
            )
        )
        bingo_lottery = Lottery(
            id=uuid4(),
            code="bingo",
            name="Audit Bingo",
            kind=LotteryKind.DAILY,
            ruleset_code="bingo_12_60_economy_v2",
            numbers_to_pick=12,
            max_number=60,
            ticket_price=50_000,
            max_tickets_per_purchase=75,
            max_tickets_per_user_per_draw=75,
            sales_cutoff_minutes=2,
            schedule={"slots": ["22:00"]},
            is_active=True,
            next_draw_number=1,
            next_ticket_number=1,
        )
        session.add(bingo_lottery)
        await session.flush()
        bingo_jackpot = JackpotAccount(
            id=uuid4(),
            lottery_id=bingo_lottery.id,
            balance=1_000_000_000,
            base_amount=1_000_000_000,
        )
        session.add(bingo_jackpot)
        session.add(
            ledger_credit(
                account_kind=LedgerAccountKind.JACKPOT,
                account_id=bingo_jackpot.id,
                amount=1_000_000_000,
                lottery_id=bingo_lottery.id,
            )
        )
    return user, lottery.id, draw.id


async def main():
    database = str(get_settings().database_url).rsplit("/", 1)[-1]
    if not database.startswith("k_loto_audit_stage1_"):
        raise RuntimeError("Requires a disposable stage1 audit database.")
    now = datetime.now(UTC)
    user, lottery_id, draw_id = await seed(now)

    async def purchase():
        async with session_factory() as session:
            return await LotteryTicketPurchaseService(session, "audit-weekly").purchase(
                user_id=user,
                combinations=[[1, 2, 3, 4, 5]],
                idempotency_key="m1-concurrent-weekly",
                now=now,
            )

    purchases = await asyncio.gather(purchase(), purchase())
    assert purchases[0].ticket_ids == purchases[1].ticket_ids
    assert sum(not result.already_processed for result in purchases) == 1
    generator = FixedNumbers()
    for _ in range(2):
        async with session_factory() as session:
            try:
                await LotterySettlementService(session, generator).settle(
                    draw_id, now=now + timedelta(hours=2)
                )
            except InsufficientReserve:
                pass
            else:
                raise AssertionError("Unfunded settlement succeeded")
        # New connection sees the persisted result after payout transaction rollback.
        async with session_factory() as session:
            draw = await session.get(Draw, draw_id)
            assert draw.status == DrawStatus.DRAWING
            assert draw.winning_numbers == [1, 2, 3, 4, 5]
            ticket = await session.get(Ticket, purchases[0].ticket_ids[0])
            assert ticket.status == TicketStatus.PURCHASED
            assert (
                await session.scalar(
                    select(func.count(LedgerTransaction.id)).where(
                        LedgerTransaction.idempotency_key.like(f"draw:{draw_id}:%")
                    )
                )
                == 0
            )
    assert generator.calls == 1
    for mutation in (
        {"winning_numbers": [6, 7, 8, 9, 10]},
        {"jackpot_opening": 0},
        {"configuration_snapshot": {}},
        {"is_distribution": True},
    ):
        try:
            async with session_factory() as session, session.begin():
                await session.execute(
                    update(Draw).where(Draw.id == draw_id).values(**mutation)
                )
        except DBAPIError as error:
            assert "Committed draw outcome is immutable" in str(error)
        else:
            raise AssertionError("Committed outcome was mutable")

    async with session_factory() as session:
        try:
            await AdminMutationService(session, user).set_jackpot(
                lottery_id,
                target_amount=0,
                reason="smoke protected obligation",
                idempotency_key="smoke-protected",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Admin spent the committed jackpot")
    async with session_factory() as session, session.begin():
        fund = await session.get(
            KasperFundAccount, KASPER_FUND_ID, with_for_update=True
        )
        fund.balance = 10_000_000
        session.add(
            ledger_credit(
                account_kind=LedgerAccountKind.KASPER_FUND,
                account_id=fund.id,
                amount=10_000_000,
            )
        )
    # A purchase into the next draw between preparation and payout stays in jackpot.
    async with session_factory() as session:
        await LotteryTicketPurchaseService(session, "audit-weekly").purchase(
            user_id=user,
            combinations=[[1, 2, 3, 4, 5]],
            idempotency_key="m1-next-weekly",
            now=now + timedelta(hours=2),
        )

    async def settle():
        async with session_factory() as session:
            return await LotterySettlementService(session, generator).settle(
                draw_id, now=now + timedelta(hours=2)
            )

    results = await asyncio.gather(settle(), settle())
    assert sum(not result.already_completed for result in results) == 1
    assert generator.calls == 1
    async with session_factory() as session:
        draw = await session.get(Draw, draw_id)
        assert draw.status == DrawStatus.COMPLETED and draw.total_payout == 2100
        jackpot = await session.scalar(
            select(JackpotAccount).where(JackpotAccount.lottery_id == lottery_id)
        )
        assert jackpot.balance == 1100
        assert (
            await session.scalar(
                select(func.sum(LedgerTransaction.amount)).where(
                    LedgerTransaction.draw_id == draw_id
                )
            )
            == 0
        )
    print("scheduled: retry outcome, rollback, concurrency, obligation and ledger PASS")

    async with session_factory() as session, session.begin():
        fund = await session.get(
            KasperFundAccount, KASPER_FUND_ID, with_for_update=True
        )
        before = fund.balance
        fund.balance += 30_000_000_000
        from k_loto.application.weekly import _ledger_entry
        from k_loto.domain.enums import TransactionType

        session.add(
            _ledger_entry(
                operation_id=uuid4(),
                idempotency_key="smoke:fund:bingo",
                account_kind=LedgerAccountKind.KASPER_FUND,
                account_id=fund.id,
                transaction_type=TransactionType.SYSTEM_ADJUSTMENT,
                before=before,
                after=fund.balance,
            )
        )
    async with session_factory() as session:
        bingo_lottery = await session.scalar(
            select(Lottery).where(Lottery.code == "bingo")
        )
        bingo_id = bingo_lottery.id
    from k_loto.application.scheduler import DrawScheduleService

    async with session_factory() as session:
        draw, _ = await DrawScheduleService(session).ensure_next_draw(
            bingo_id, reference=now
        )
        bingo_draw_id = draw.id

    async def buy_bingo(key):
        async with session_factory() as session:
            return await LotteryTicketPurchaseService(
                session, "bingo", bingo_draw_id
            ).purchase(
                user_id=user,
                combinations=[[]],
                select_bingo_pool=True,
                idempotency_key=key,
                now=now,
            )

    async def cancel(key):
        async with session_factory() as session:
            return await PurchaseReceiptService(session).cancel_uncommitted(
                user, key, "scheduled"
            )

    purchased = await buy_bingo("m1-bingo-lost-answer")
    receipt = await cancel("m1-bingo-lost-answer")
    assert receipt.ticket_ids == purchased.ticket_ids
    repeated = await buy_bingo("m1-bingo-lost-answer")
    assert repeated.ticket_ids == purchased.ticket_ids and repeated.already_processed
    assert await cancel("m1-bingo-cancel-first") is None
    try:
        await buy_bingo("m1-bingo-cancel-first")
    except InvalidTicket:
        pass
    else:
        raise AssertionError("Cancelled Bingo purchase succeeded")
    raced = await asyncio.gather(
        buy_bingo("m1-bingo-race"), cancel("m1-bingo-race"), return_exceptions=True
    )
    if isinstance(raced[0], InvalidTicket):
        assert raced[1] is None
    else:
        assert raced[0].ticket_ids == raced[1].ticket_ids
    print("bingo: receipt, replay, cancelled attempt and purchase/cancel race PASS")

    # Persist the broadcast then settle it: ordinary payouts plus jackpot must balance.
    original = bingo.generate_sequence
    async with session_factory() as session:
        purchased_ticket = await session.get(Ticket, purchased.ticket_ids[0])
        numbers = purchased_ticket.numbers
    sequence = tuple(numbers + [n for n in range(1, 61) if n not in numbers])[:58]
    bingo.generate_sequence = lambda: sequence
    try:
        async with session_factory() as session:
            await LotterySettlementService(session).settle(
                bingo_draw_id, now=draw.scheduled_at
            )
    finally:
        bingo.generate_sequence = original
    async with session_factory() as session:
        try:
            await AdminMutationService(session, user).set_jackpot(
                bingo_id,
                target_amount=0,
                reason="smoke bingo broadcast",
                idempotency_key="smoke-bingo-protected",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Bingo broadcast jackpot was reduced")
    async with session_factory() as session:
        await LotterySettlementService(session).settle(
            bingo_draw_id, now=draw.scheduled_at + timedelta(seconds=120)
        )
    async with session_factory() as session:
        assert (
            await session.scalar(
                select(func.sum(LedgerTransaction.amount)).where(
                    LedgerTransaction.draw_id == bingo_draw_id
                )
            )
            == 0
        )
    async with session_factory() as session:
        card = await session.get(Ticket, purchased.ticket_ids[0])
        assert [card.bingo_result["amounts"][i] for i in (0, 1, 3)] == [
            50_000,
            100_000,
            20_000,
        ]
        assert (
            await session.scalar(
                select(func.count(BingoPoolTicket.id)).where(
                    BingoPoolTicket.draw_id == bingo_draw_id,
                    BingoPoolTicket.ticket_id.is_(None),
                )
            )
            == 0
        )
        assert (
            await session.scalar(
                select(func.count(BingoPoolTicket.id)).where(
                    BingoPoolTicket.ticket_id == card.id,
                )
            )
            == 1
        )
    print(
        "bingo: stacked fixed prizes, jackpot protection, "
        "unused cleanup and ledger PASS"
    )

    await verify_dual(user, now)

    async with session_factory() as session, session.begin():
        fund = await session.get(
            KasperFundAccount, KASPER_FUND_ID, with_for_update=True
        )
        before = fund.balance
        fund.balance = 0
        session.add(
            _ledger_entry(
                operation_id=uuid4(),
                idempotency_key="smoke:fund:instant",
                account_kind=LedgerAccountKind.KASPER_FUND,
                account_id=fund.id,
                transaction_type=TransactionType.SYSTEM_ADJUSTMENT,
                before=before,
                after=0,
            )
        )

    class NoRandomness:
        def draw_sequence(self, *args):
            raise AssertionError("Insolvent instant purchase consumed randomness")

    async with session_factory() as session:
        try:
            await InstantTicketPurchaseService(
                session, NoRandomness(), game_code="vault"
            ).purchase(
                user_id=user,
                quantity=3,
                idempotency_key="m1-insolvent-vault",
            )
        except ConfigurationError:
            pass
        else:
            raise AssertionError("Insolvent instant purchase was accepted")
    print("instant: full batch coverage checked before RNG PASS")
    await engine.dispose()


async def verify_dual(user, now):
    from k_loto.domain.dual import (
        DUAL_ECONOMY_MAX_PRIZE as DUAL_JACKPOT,
    )
    from k_loto.domain.dual import (
        DUAL_ECONOMY_PRICE as DUAL_PRICE,
    )
    from k_loto.domain.lottery_rules import DUAL_ECONOMY_RULES as DUAL_RULES

    first_at = now.replace(hour=21, minute=30, second=0, microsecond=0) + timedelta(
        days=1
    )
    async with session_factory() as session, session.begin():
        lottery = Lottery(
            id=uuid4(),
            code="dual",
            name="Audit Dual",
            kind=LotteryKind.DAILY,
            ruleset_code=DUAL_RULES.code,
            max_tickets_per_purchase=50,
            max_tickets_per_user_per_draw=50,
            numbers_to_pick=4,
            max_number=24,
            ticket_price=DUAL_PRICE,
            sales_cutoff_minutes=2,
            is_active=True,
            schedule={"slots": ["00:30", "07:30"]},
            next_draw_number=3,
            next_ticket_number=1,
        )
        session.add(lottery)
        await session.flush()
        jackpot = JackpotAccount(
            id=uuid4(),
            lottery_id=lottery.id,
            balance=DUAL_JACKPOT,
            base_amount=DUAL_JACKPOT,
        )
        session.add(jackpot)
        session.add(
            ledger_credit(
                account_kind=LedgerAccountKind.JACKPOT,
                account_id=jackpot.id,
                amount=DUAL_JACKPOT,
                lottery_id=lottery.id,
            )
        )
        draws = []
        for number, at in enumerate((first_at, first_at + timedelta(hours=7)), 1):
            draw = Draw(
                id=uuid4(),
                lottery_id=lottery.id,
                public_number=number,
                status=DrawStatus.SCHEDULED,
                scheduled_at=at,
                sales_close_at=at - timedelta(minutes=2),
                correlation_id=uuid4(),
            )
            session.add(draw)
            draws.append(draw)
    async with session_factory() as session:
        bought = await LotteryTicketPurchaseService(session, "dual").purchase(
            user_id=user,
            combinations=[[3, 10, 15, 22]],
            idempotency_key="m1-dual-rounds",
            now=now,
        )

    class DualNumbers:
        calls = 0

        def draw(self, population_size, numbers_to_pick):
            assert (population_size, numbers_to_pick) == (12, 2)
            self.calls += 1
            return (3, 10)

    generator = DualNumbers()
    for draw in draws:
        for replay in (False, True):
            async with session_factory() as session:
                result = await LotterySettlementService(session, generator).settle(
                    draw.id, now=draw.scheduled_at
                )
                assert result.already_completed == replay
    async with session_factory() as session:
        ticket = await session.get(Ticket, bought.ticket_ids[0])
        assert ticket.status == TicketStatus.SETTLED
        assert ticket.prize_amount == DUAL_JACKPOT
        assert (
            await session.scalar(
                select(func.sum(LedgerTransaction.amount)).where(
                    LedgerTransaction.draw_id == draws[1].id
                )
            )
            == 0
        )
    assert generator.calls == 2
    print("dual: both persisted outcomes, idempotent payout and ledger PASS")


if __name__ == "__main__":
    asyncio.run(main())
