"""Distribution accounting/concurrency checks on an isolated backup clone only."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import func, select, text

from k_loto.application.distribution import (
    DistributionDrawService,
    deliver_distribution,
    queue_result,
)
from k_loto.application.weekly import (
    LotterySettlementService,
    LotteryTicketPurchaseService,
    _ledger_entry,
    draw_configuration_snapshot,
)
from k_loto.core.config import get_settings
from k_loto.domain.enums import DrawStatus, LedgerAccountKind, TransactionType
from k_loto.domain.lottery_rules import (
    GRAND_ECONOMY_RULES,
    GRAND_FIXED_RULES,
    get_lottery_rules,
)
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    Balance,
    DistributionAnnouncement,
    Draw,
    JackpotAccount,
    JackpotWinEvent,
    LedgerTransaction,
    Lottery,
    User,
)
from k_loto.infrastructure.database.session import engine, session_factory


class Fixed:
    def draw(self, population, count):
        assert (population, count) in {(35, 5), (5, 2)}
        return tuple(range(1, count + 1))


async def main():
    if (
        not str(get_settings().database_url)
        .rstrip("/")
        .endswith("/k_loto_distribution_smoke")
    ):
        raise RuntimeError(
            "Only the disposable distribution smoke database is allowed."
        )
    uid, did = uuid4(), uuid4()
    now = datetime.now(UTC)
    async with session_factory() as s, s.begin():
        old_tickets = await s.scalar(
            text(
                "SELECT md5(coalesce(string_agg(row_to_json(t)::text, '' "
                "ORDER BY id), '')) FROM tickets t"
            )
        )
        old_draws = await s.scalar(
            text(
                "SELECT md5(coalesce(string_agg(row_to_json(t)::text, '' "
                "ORDER BY id), '')) FROM draws t WHERE status='COMPLETED'"
            )
        )
        lottery = await s.scalar(select(Lottery).where(Lottery.code == "weekly"))
        assert lottery and lottery.ruleset_code in (
            GRAND_FIXED_RULES.code,
            GRAND_ECONOMY_RULES.code,
        )
        rules = get_lottery_rules(lottery.ruleset_code)
        ordinary_prizes = rules.fixed_payouts[51] * 2 + rules.fixed_payouts[42]
        lid = lottery.id
        jackpot = await s.scalar(
            select(JackpotAccount).where(JackpotAccount.lottery_id == lid)
        )
        assert jackpot
        s.add(
            User(id=uid, display_name="Disposable distribution check", is_active=True)
        )
        await s.flush()
        s.add(Balance(user_id=uid, amount=1_000_000, version=1))
        s.add(
            _ledger_entry(
                operation_id=uuid4(),
                idempotency_key=f"smoke-seed:{uid}",
                account_kind=LedgerAccountKind.USER_BALANCE,
                account_id=uid,
                transaction_type=TransactionType.SYSTEM_ADJUSTMENT,
                before=0,
                after=1_000_000,
                user_id=uid,
                details={"reason": "Disposable clone only"},
            )
        )
        last = await s.scalar(
            select(func.max(Draw.scheduled_at)).where(Draw.lottery_id == lid)
        )
        stamp = max(last, now) + timedelta(days=7)
        s.add(
            Draw(
                id=did,
                lottery_id=lid,
                public_number=lottery.next_draw_number,
                status=DrawStatus.SCHEDULED,
                scheduled_at=stamp,
                sales_close_at=stamp - timedelta(minutes=5),
                correlation_id=uuid4(),
                ticket_count=0,
                total_sales=0,
                total_payout=0,
                reserve_used=0,
                configuration_snapshot=draw_configuration_snapshot(
                    lottery, jackpot.base_amount
                ),
            )
        )
        lottery.next_draw_number += 1
    async with session_factory() as s:
        bought = await LotteryTicketPurchaseService(
            s, lottery_code="weekly", target_draw_id=did
        ).purchase(
            user_id=uid,
            combinations=[
                [1, 2, 3, 4, 5, 36, 38],
                [1, 2, 3, 4, 5, 36, 39],
                [1, 2, 3, 4, 6, 36, 37],
            ],
            idempotency_key=f"distribution-smoke:{uid}",
            now=now,
        )
        assert not bought.already_processed
    async with session_factory() as s:
        before_money = await s.scalar(
            select(Balance.amount).where(Balance.user_id == uid)
        )
        opening = await s.scalar(
            select(JackpotAccount.balance).where(JackpotAccount.lottery_id == lid)
        )
        base = await s.scalar(
            select(JackpotAccount.base_amount).where(JackpotAccount.lottery_id == lid)
        )

    async def assign():
        async with session_factory() as s:
            return await DistributionDrawService(s).assign(did, uid, now=now)

    results = await asyncio.gather(assign(), assign())
    assert all(r["is_distribution"] and r["ticket_count"] == 3 for r in results)
    async with session_factory() as s:
        assert (
            await s.scalar(
                select(func.count(DistributionAnnouncement.id)).where(
                    DistributionAnnouncement.draw_id == did
                )
            )
            == 1
        )
        assert (
            await s.scalar(
                select(func.count(AdminAuditLog.id)).where(
                    AdminAuditLog.entity_id == did
                )
            )
            == 1
        )
        assert (
            await s.scalar(select(Balance.amount).where(Balance.user_id == uid))
            == before_money
        )

    async def settle():
        async with session_factory() as s:
            return await LotterySettlementService(s, Fixed()).settle(did, now=stamp)

    def fail_after_result(*args, **kwargs):
        queue_result(*args, **kwargs)
        raise RuntimeError("injected result rollback")

    with patch(
        "k_loto.application.distribution.queue_result", side_effect=fail_after_result
    ):
        try:
            await settle()
        except RuntimeError as error:
            assert str(error) == "injected result rollback"
        else:
            raise AssertionError("Result outbox rollback failed")
    async with session_factory() as s:
        assert (
            await s.scalar(
                select(func.count(DistributionAnnouncement.id)).where(
                    DistributionAnnouncement.draw_id == did
                )
            )
            == 1
        )
        assert (
            await s.scalar(select(Balance.amount).where(Balance.user_id == uid))
            == before_money
        )

    with patch(
        "k_loto.application.weekly._ledger_entry",
        side_effect=RuntimeError("injected rollback"),
    ):
        try:
            await settle()
        except RuntimeError as error:
            assert str(error) == "injected rollback"
        else:
            raise AssertionError("Rollback failed")
    async with session_factory() as s:
        assert (
            await s.scalar(select(Balance.amount).where(Balance.user_id == uid))
            == before_money
        )
        assert (
            await s.scalar(select(Draw.status).where(Draw.id == did))
            == DrawStatus.SCHEDULED
        )
        assert (
            await s.scalar(
                select(JackpotAccount.balance).where(JackpotAccount.lottery_id == lid)
            )
            == opening
        )
    settled = await asyncio.gather(settle(), settle())
    assert sum(r.already_completed for r in settled) == 1
    async with session_factory() as s:
        draw = await s.get(Draw, did)
        assert draw.distribution_category == "51" and draw.distributed_amount == opening
        assert draw.total_payout == opening + ordinary_prizes
        assert (
            await s.scalar(
                select(JackpotAccount.balance).where(JackpotAccount.lottery_id == lid)
            )
            == base
        )
        assert (
            await s.scalar(select(Balance.amount).where(Balance.user_id == uid))
            == before_money + opening + ordinary_prizes
        )
        ledger = (
            await s.scalars(
                select(LedgerTransaction).where(
                    LedgerTransaction.draw_id == did,
                    LedgerTransaction.type != TransactionType.TICKET_PURCHASE,
                )
            )
        ).all()
        assert sum(entry.amount for entry in ledger) == 0
        assert (
            await s.scalar(
                select(func.count(JackpotWinEvent.id)).where(
                    JackpotWinEvent.draw_id == did
                )
            )
            == 0
        )
        assert (
            await s.scalar(
                text(
                    "SELECT md5(coalesce(string_agg(row_to_json(t)::text, '' "
                    "ORDER BY id), '')) FROM tickets t WHERE user_id != :uid"
                ).bindparams(uid=uid)
            )
            == old_tickets
        )
        assert (
            await s.scalar(
                text(
                    "SELECT md5(coalesce(string_agg(row_to_json(t)::text, '' "
                    "ORDER BY id), '')) FROM draws t WHERE status='COMPLETED' "
                    "AND id != :did"
                ).bindparams(did=did)
            )
            == old_draws
        )

    class MockBot:
        calls = 0

        async def send_message(self, *args, **kwargs):
            self.calls += 1
            assert (
                "РаспределительныйТираж" in kwargs["text"]
                and kwargs["parse_mode"] is None
            )
            return SimpleNamespace(message_id=123)

    bot = MockBot()
    assert await deliver_distribution(session_factory, bot, now=now) == "sent"
    assert await deliver_distribution(session_factory, bot, now=stamp) == "sent"
    assert await deliver_distribution(session_factory, bot, now=stamp) == "empty"
    assert bot.calls == 2
    from scripts.distribution_followup_smoke import verify_followup

    await verify_followup(uid, lid, did, stamp, now)
    print(
        "Distribution clone: concurrent assignment/settlement, rollback, "
        "full jackpot, ordinary prizes, ledger zero sum, immutable history "
        "and separate mocked schedule/result delivery PASS"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
