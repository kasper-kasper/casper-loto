"""Real PostgreSQL regression for the planned pause, refunds and epoch archive."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select, text

from k_loto.application.admin import AdminQueryService
from k_loto.application.economy import control_state, require_open
from k_loto.application.economy_archive import apply_archive_scope
from k_loto.application.economy_transition import EconomyTransitionService
from k_loto.application.instant import InstantTicketPurchaseService
from k_loto.application.scheduler import DrawRecoveryService, DrawScheduleService
from k_loto.application.weekly import (
    KASPER_FUND_ID,
    LotterySettlementService,
    LotteryTicketPurchaseService,
    draw_configuration_snapshot,
)
from k_loto.core.config import get_settings
from k_loto.domain.enums import DrawStatus, LedgerAccountKind, LotteryKind, TicketStatus
from k_loto.domain.errors import InvalidStateTransition
from k_loto.domain.lottery_rules import (
    LEGACY_CODE_V2_RULES,
    LEGACY_FLASH_V3_RULES,
    LEGACY_PULSE_V4_RULES,
)
from k_loto.domain.schedules import next_draw_at
from k_loto.infrastructure.database.models import (
    Balance,
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


async def history_hash():
    async with engine.connect() as connection:
        return (
            await connection.execute(
                text(
                    "SELECT md5(coalesce(string_agg(row_to_json(d)::text, '' "
                    "ORDER BY id), '')) FROM draws d WHERE status = 'COMPLETED'"
                )
            )
        ).scalar_one()


async def main():
    if (
        not get_settings()
        .database_url.path.lstrip("/")
        .startswith("k_loto_audit_stage1_")
    ):
        raise RuntimeError("Disposable audit database required.")
    now = datetime.now(UTC)
    user, owner = uuid4(), uuid4()
    ids, counters = {}, {}
    async with session_factory() as session, session.begin():
        session.add_all(
            [
                User(id=user, display_name="Pause audit"),
                User(id=owner, display_name="Owner audit", is_admin=True),
            ]
        )
        await session.flush()
        session.add(Balance(user_id=user, amount=10_000_000))
        session.add(KasperFundAccount(id=KASPER_FUND_ID, balance=1_000_000_000))
        for kind, account, amount in (
            (LedgerAccountKind.USER_BALANCE, user, 10_000_000),
            (LedgerAccountKind.KASPER_FUND, KASPER_FUND_ID, 1_000_000_000),
        ):
            session.add(
                ledger_credit(
                    account_kind=kind,
                    account_id=account,
                    amount=amount,
                    user_id=user if kind == LedgerAccountKind.USER_BALANCE else None,
                )
            )
        for code, rule in (
            ("flash", LEGACY_FLASH_V3_RULES),
            ("shadow", LEGACY_CODE_V2_RULES),
            ("pulse", LEGACY_PULSE_V4_RULES),
        ):
            lottery = Lottery(
                id=uuid4(),
                code=code,
                name=rule.label,
                kind=LotteryKind.DAILY,
                ruleset_code=rule.code,
                numbers_to_pick=rule.numbers_to_pick,
                max_number=rule.max_number,
                ticket_price=2000,
                sales_cutoff_minutes=0,
                schedule={
                    "type": "interval",
                    "interval_minutes": 9,
                    "future_draw_count": 2,
                },
                is_active=True,
                next_draw_number=1002,
                next_ticket_number=2001,
                max_tickets_per_purchase=100,
                max_tickets_per_user_per_draw=500,
            )
            session.add(lottery)
            await session.flush()
            jackpot = JackpotAccount(
                id=uuid4(),
                lottery_id=lottery.id,
                balance=1_000_000,
                base_amount=1_000_000,
            )
            session.add(jackpot)
            session.add(
                ledger_credit(
                    account_kind=LedgerAccountKind.JACKPOT,
                    account_id=jackpot.id,
                    amount=jackpot.balance,
                    lottery_id=lottery.id,
                )
            )
            draw = Draw(
                id=uuid4(),
                lottery_id=lottery.id,
                public_number=1001,
                status=DrawStatus.SCHEDULED,
                scheduled_at=now + timedelta(hours=1),
                sales_close_at=now + timedelta(hours=1),
                correlation_id=uuid4(),
                configuration_snapshot=draw_configuration_snapshot(lottery, 1_000_000),
            )
            session.add(draw)
            ids[code] = (lottery.id, draw.id)
        # Cancelled reservations after reopening (including a month ahead) must
        # not delay the first new draw or monopolize its calendar slot.
        for number, scheduled in (
            (
                1002,
                next_draw_at(
                    LotteryKind.DAILY,
                    now + timedelta(hours=6),
                    {"type": "interval", "interval_minutes": 9},
                ),
            ),
            (1003, now + timedelta(days=30)),
        ):
            session.add(
                Draw(
                    id=uuid4(),
                    lottery_id=ids["flash"][0],
                    public_number=number,
                    status=DrawStatus.SCHEDULED,
                    scheduled_at=scheduled,
                    sales_close_at=scheduled,
                    correlation_id=uuid4(),
                    configuration_snapshot={"ruleset_code": LEGACY_FLASH_V3_RULES.code},
                )
            )
        flash = await session.get(Lottery, ids["flash"][0])
        flash.next_draw_number = 1004
        # A completed old draw must remain byte-for-byte unchanged.
        old = Draw(
            id=uuid4(),
            lottery_id=ids["flash"][0],
            public_number=1000,
            status=DrawStatus.SCHEDULED,
            scheduled_at=now - timedelta(minutes=9),
            sales_close_at=now - timedelta(minutes=9),
            correlation_id=uuid4(),
            configuration_snapshot={
                "ruleset_code": LEGACY_FLASH_V3_RULES.code,
                "ticket_price": 2000,
                "base_jackpot": 1_000_000,
            },
        )
        session.add(old)
    async with session_factory() as session:
        await LotterySettlementService(session).settle(old.id, now=now)
    for code, numbers in (
        ("flash", [1, 2, 3, 4, 5]),
        ("shadow", [0, 0, 0, 0, 0]),
        ("pulse", [1, 2, 13, 14]),
    ):
        async with session_factory() as session:
            await LotteryTicketPurchaseService(
                session, code, target_draw_id=ids[code][1]
            ).purchase(
                user_id=user,
                combinations=[numbers],
                idempotency_key=f"pause-old-{code}",
                now=now,
            )
    async with session_factory() as session:
        for lottery in (await session.scalars(select(Lottery))).all():
            counters[lottery.id] = (
                lottery.next_draw_number,
                lottery.next_ticket_number,
            )
    before_hash = await history_hash()

    # The exclusive transition must wait for an in-flight shared business lock.
    holder = session_factory()
    await holder.begin()
    await require_open(holder)

    async def activate():
        async with session_factory() as session:
            return await EconomyTransitionService(session).activate(
                owner_id=owner, cutoff=now
            )

    transition = asyncio.create_task(activate())
    await asyncio.sleep(0.1)
    assert not transition.done()
    await holder.commit()
    await holder.close()
    result = await transition
    assert result["refunded_tickets"] == 3 and result["refunded_cas"] == 6000
    assert (await activate())["already_applied"] is True
    assert before_hash == await history_hash()
    async with session_factory() as session:
        control = await control_state(session)
        assert control.paused and control.epoch == 2 and control.recovery_after is None
        started = control.epoch_started_at
        assert (
            await session.scalar(select(Balance.amount).where(Balance.user_id == user))
            == 10_000_000
        )
        assert (
            await session.scalar(
                select(func.count(Ticket.id)).where(
                    Ticket.status == TicketStatus.REFUNDED
                )
            )
            == 3
        )
        assert (
            await session.scalar(
                select(func.sum(LedgerTransaction.amount)).where(
                    LedgerTransaction.type == "TICKET_REFUND"
                )
            )
            == 0
        )
        for lottery in (await session.scalars(select(Lottery))).all():
            assert counters[lottery.id] == (
                lottery.next_draw_number,
                lottery.next_ticket_number,
            )
    for archive, expected in ((False, 0), (True, 3)):
        async with session_factory() as session:
            apply_archive_scope(session, epoch=2, started_at=started, archive=archive)
            assert await session.scalar(select(func.count(Ticket.id))) == expected
            # Real ORM aggregate and correlated-subquery paths, not generated SQL alone.
            counts = await AdminQueryService(session).dashboard_counts()
            players = await AdminQueryService(session).players()
            assert counts["tickets"] == expected
            assert (
                next(player for player in players if player.id == user).ticket_count
                == expected
            )
            await AdminQueryService(session).ticket_analytics()
    for operation in ("draw", "purchase", "instant", "schedule"):
        async with session_factory() as session:
            try:
                if operation == "draw":
                    await LotterySettlementService(session).settle(
                        ids["flash"][1], now=now + timedelta(days=1)
                    )
                elif operation == "purchase":
                    await LotteryTicketPurchaseService(session, "flash").purchase(
                        user_id=user,
                        combinations=[[1, 2, 3, 4, 5]],
                        idempotency_key="paused-buy",
                    )
                elif operation == "instant":
                    await InstantTicketPurchaseService(session).purchase(
                        user_id=user, quantity=1, idempotency_key="paused-instant"
                    )
                else:
                    await DrawScheduleService(session).ensure_next_draw(
                        ids["flash"][0], reference=now
                    )
            except InvalidStateTransition:
                pass
            else:
                raise AssertionError("Paused domain operation unexpectedly allowed")
    assert not (
        await DrawRecoveryService(session_factory).reconcile(
            now=now + timedelta(days=2)
        )
    ).settled_draw_ids

    # Test explicit reopening only on this disposable database, then restart recovery.
    resume = now + timedelta(hours=6)
    async with session_factory() as session:
        await EconomyTransitionService(session).resume(owner_id=owner, now=resume)
    async with session_factory() as session:
        fresh, _ = await DrawScheduleService(session).ensure_next_draw(
            ids["flash"][0], reference=resume
        )
    assert fresh.scheduled_at == next_draw_at(
        LotteryKind.DAILY, resume, {"type": "interval", "interval_minutes": 9}
    )
    assert fresh.public_number == counters[ids["flash"][0]][0]
    assert fresh.configuration_snapshot["economy_epoch"] == 2
    async with session_factory() as session:
        before = await session.scalar(
            select(JackpotAccount.balance).where(
                JackpotAccount.lottery_id == ids["flash"][0]
            )
        )
    async with session_factory() as session:
        purchase = await LotteryTicketPurchaseService(
            session, "flash", target_draw_id=fresh.id
        ).purchase(
            user_id=user,
            combinations=[[1, 2, 3, 4, 5]] * 25,
            idempotency_key="new-fast-buy",
            now=resume,
        )
    async with session_factory() as session:
        after = await session.scalar(
            select(JackpotAccount.balance).where(
                JackpotAccount.lottery_id == ids["flash"][0]
            )
        )
        assert purchase.total_cost == 50_000 and after - before == 20_000
        assert (
            await session.scalar(
                select(func.sum(LedgerTransaction.amount)).where(
                    LedgerTransaction.operation_id == purchase.operation_id
                )
            )
            == -30_000
        )
    report = await DrawRecoveryService(session_factory).reconcile(
        now=resume + timedelta(minutes=30)
    )
    assert not report.failed_lottery_ids
    async with session_factory() as session:
        assert (
            await session.scalar(
                select(func.count(Draw.id)).where(
                    Draw.scheduled_at > now,
                    Draw.scheduled_at <= resume,
                    Draw.status != DrawStatus.CANCELLED,
                )
            )
            == 0
        )
    assert (
        before_hash != await history_hash()
    )  # genuine post-resume draws were recovered
    print(json.dumps({"pause_refund_archive_resume": "PASS", **result}))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
