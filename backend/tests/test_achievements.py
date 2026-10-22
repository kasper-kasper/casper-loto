"""Achievement rule regressions and opt-in real PostgreSQL transactions."""

import asyncio
import json
import os
from datetime import UTC, date, datetime, timedelta
from time import perf_counter
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import event as sql_event
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from k_loto.api.dependencies import (
    CurrentMiniAppUser,
    get_current_miniapp_user,
    get_db_session,
)
from k_loto.application.achievement_catalog import (
    CatalogEntry,
    import_catalog,
    launch_local,
)
from k_loto.application.achievement_results import ticket_result
from k_loto.application.achievements import (
    AchievementProjection,
    Catalog,
    drain,
    enqueue,
    execute_rewards,
    process_one,
    record_activity,
)
from k_loto.application.weekly import LotteryTicketPurchaseService, _ledger_entry
from k_loto.core.config import get_settings
from k_loto.domain.achievements import Condition, activity_progress
from k_loto.domain.enums import (
    DrawStatus,
    LedgerAccountKind,
    LotteryKind,
    TicketStatus,
    TransactionType,
)
from k_loto.domain.lottery_rules import LOTTERY_RULES
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementCorrection,
    AchievementEvent,
    AchievementPlayer,
)
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    JackpotAccount,
    LedgerTransaction,
    Lottery,
    Ticket,
    User,
)
from k_loto.main import create_app


def entry(
    code="test-purchase", metric="paid_tickets", target=10, rewards=None, **kwargs
):
    return CatalogEntry.model_validate(
        dict(
            code=code,
            version=1,
            rarity="common",
            title="Temporary test fixture",
            description="Not a product achievement",
            active=True,
            condition={"conditions": [{"metric": metric, "target": target}]},
            rewards=rewards or [],
            **kwargs,
        )
    )


@pytest.mark.parametrize(
    "invalid",
    [
        {"metric": "sql", "target": 1},
        {"metric": "paid_tickets", "target": 1.0},
        {"metric": "paid_tickets", "target": True},
        {"metric": "paid_tickets", "target": 1, "sql": "SELECT 1"},
        {"metric": "current_balance", "target": 1, "lottery": "bingo"},
        {"metric": "earned_category", "target": 1},
        {"metric": "qualifying_wins", "target": 1},
        {"metric": "paid_tickets", "target": 1, "min_prize": 10},
    ],
)
def test_invalid_conditions_fail_closed(invalid):
    with pytest.raises(ValidationError):
        Condition.model_validate(invalid)


def test_integer_multiplier_and_stable_filter_identity():
    c = Condition(
        metric="qualifying_wins",
        target=2,
        multiplier_numerator=3,
        multiplier_denominator=2,
    )
    result = dict(
        lottery="bingo",
        prize=4_999,
        standard_price=3_333,
        matches=0,
        natural_jackpot=False,
        categories=[],
    )
    assert not c.matches_result(result)
    result["prize"] = 5_000
    assert c.matches_result(result)
    assert c.key == c.model_copy(update={"target": 100}).key


def test_moscow_days_streak_and_late_duplicate():
    assert activity_progress(None, date(2026, 10, 18), 0) == (1, 1)
    assert activity_progress("2026-10-18", date(2026, 10, 18), 4) == (0, 4)
    assert activity_progress("2026-10-18", date(2026, 10, 19), 4) == (1, 5)
    assert activity_progress("2026-10-18", date(2026, 10, 20), 4) == (1, 1)
    assert activity_progress("2026-10-18", date(2026, 10, 17), 4) == (0, 4)


@pytest.mark.parametrize("rules", list(LOTTERY_RULES.values()), ids=lambda r: r.code)
def test_jackpot_uses_existing_rules_and_excludes_distribution(rules):
    ticket = SimpleNamespace(
        prize_amount=10_000,
        purchase_price=3333,
        matches=rules.jackpot_match,
        bingo_result=None,
    )
    draw = SimpleNamespace(
        configuration_snapshot={"ruleset_code": rules.code, "ticket_price": 3333},
        is_distribution=False,
    )
    lottery = SimpleNamespace(code="test", ruleset_code=rules.code)
    assert ticket_result(ticket, draw, lottery)["natural_jackpot"]
    draw.is_distribution = True
    assert not ticket_result(ticket, draw, lottery)["natural_jackpot"]


def test_bingo_card_prizes_and_natural_jackpot_are_distinct():
    ticket = SimpleNamespace(
        prize_amount=170_000,
        purchase_price=50_000,
        matches=12,
        bingo_result={"amounts": [50_000, 100_000, 0, 20_000]},
    )
    draw = SimpleNamespace(
        configuration_snapshot={"ruleset_code": "bingo_12_60_economy_v2"},
        is_distribution=False,
    )
    lottery = SimpleNamespace(code="bingo", ruleset_code="bingo_12_60_economy_v2")
    result = ticket_result(ticket, draw, lottery)
    assert result["prize"] == 170_000 and result["prizes"] == 3
    assert not result["natural_jackpot"]
    ticket.bingo_result["amounts"][2] = 1_000_000
    assert ticket_result(ticket, draw, lottery)["natural_jackpot"]
    draw.is_distribution = True
    assert not ticket_result(ticket, draw, lottery)["natural_jackpot"]


@pytest_asyncio.fixture
async def pg(monkeypatch):
    configured = os.environ.get("ACHIEVEMENT_TEST_DATABASE_URL")
    if not configured:
        pytest.skip(
            "Set explicit local ACHIEVEMENT_TEST_DATABASE_URL for PostgreSQL tests"
        )
    url = make_url(configured)
    assert url.host in {"127.0.0.1", "localhost"} and url.database in {
        "k_loto_achievement_test",
        "k_loto_achievement_fresh",
    }
    name = f"k_loto_achievement_{uuid4().hex}"
    admin = create_async_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    created = False
    try:
        async with admin.connect() as connection:
            await connection.execute(
                text(f'CREATE DATABASE "{name}" TEMPLATE "{url.database}"')
            )
            created = True
        engine = create_async_engine(url.set(database=name), poolclass=NullPool)
        monkeypatch.setenv("APP_ENV", "test")
        get_settings.cache_clear()
        factory = async_sessionmaker(engine, expire_on_commit=False)
        yield factory
        await engine.dispose()
    finally:
        if created:
            async with admin.connect() as connection:
                await connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        await admin.dispose()
        get_settings.cache_clear()


async def seed(factory, *, amount=1_000_000):
    uid, lid, did = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    async with factory() as s, s.begin():
        s.add(User(id=uid, display_name="Achievement synthetic player"))
        s.add(
            Lottery(
                id=lid,
                code=f"achievement-{lid.hex[:8]}",
                name="Synthetic lottery",
                kind=LotteryKind.WEEKLY,
                ruleset_code="weekly_5_20",
                numbers_to_pick=5,
                max_number=20,
                ticket_price=10,
                sales_cutoff_minutes=5,
                schedule={},
            )
        )
        await s.flush()
        s.add(Balance(user_id=uid, amount=amount))
        s.add(
            Draw(
                id=did,
                lottery_id=lid,
                public_number=1,
                status=DrawStatus.SCHEDULED,
                scheduled_at=now + timedelta(days=5),
                sales_close_at=now + timedelta(days=4),
                configuration_snapshot={
                    "ruleset_code": "weekly_5_20",
                    "ticket_price": 10,
                },
            )
        )
    return uid, lid, did


async def tickets(factory, uid, lid, did, count, start=1):
    values = [
        dict(
            id=uuid4(),
            user_id=uid,
            lottery_id=lid,
            draw_id=did,
            public_number=n,
            numbers=[1, 2, 3, 4, 5],
            purchase_price=10,
            purchased_at=datetime.now(UTC),
        )
        for n in range(start, start + count)
    ]
    async with factory() as s, s.begin():
        await s.execute(insert(Ticket), values)
    return [v["id"] for v in values]


async def launch(factory, entries):
    async with factory() as s, s.begin():
        await import_catalog(s, entries)
        await launch_local(s)
    await drain(factory, limit=100)


async def quiet(factory):
    # Draw pages yield via available_at, not a busy loop in the worker.
    for _ in range(200):
        await drain(factory, limit=100)
        async with factory() as s:
            pending = await s.scalar(
                select(func.count())
                .select_from(AchievementEvent)
                .where(AchievementEvent.processed_at.is_(None))
            )
            errors = list(
                (
                    await s.scalars(
                        select(AchievementEvent.last_error).where(
                            AchievementEvent.last_error.is_not(None)
                        )
                    )
                ).all()
            )
        assert not errors, errors
        if not pending:
            return
        await asyncio.sleep(0.02)
    raise AssertionError("Queue did not drain")


async def metrics(factory, uid):
    async with factory() as s:
        return dict((await s.get(AchievementPlayer, uid)).metrics)


@pytest.mark.asyncio
async def test_pg_launch_boundary_bulk_purchase_refund_and_award_retention(pg):
    uid, lid, did = await seed(pg)
    old = await tickets(pg, uid, lid, did, 3)
    async with pg() as s:
        assert await s.scalar(select(func.count()).select_from(AchievementEvent)) == 0
    await launch(pg, [entry(rewards=[{"type": "cas", "amount": 3333}])])
    ids = await tickets(pg, uid, lid, did, 10, start=4)
    await quiet(pg)
    m = await metrics(pg, uid)
    assert m["paid_tickets"] == 10 and m["draw_participations"] == 1
    assert m["spent_tickets"] == 100 and m["lotteries_count"] == 1
    async with pg() as s:
        assert (await s.get(Balance, uid)).amount == 1_003_333
        assert await s.scalar(select(func.count()).select_from(AchievementAward)) == 1
        assert (
            await s.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(
                    LedgerTransaction.type == TransactionType.ACHIEVEMENT_REWARD,
                    LedgerTransaction.account_kind == LedgerAccountKind.USER_BALANCE,
                )
            )
            == 1
        )
    async with pg() as s, s.begin():
        await s.execute(
            update(Ticket)
            .where(Ticket.id.in_(ids + old))
            .values(status=TicketStatus.REFUNDED)
        )
    await quiet(pg)
    m = await metrics(pg, uid)
    assert (
        m["paid_tickets"]
        == m["spent_tickets"]
        == m["draw_participations"]
        == m["lotteries_count"]
        == 0
    )
    async with pg() as s:
        assert (
            await s.scalar(select(func.count()).select_from(AchievementCorrection)) == 1
        )
        assert await s.scalar(select(func.count()).select_from(AchievementAward)) == 1
    async with pg() as s, s.begin():
        with pytest.raises(ValueError, match="once-only"):
            await launch_local(s)


@pytest.mark.asyncio
async def test_pg_duplicate_events_parallel_rewards_and_wallet_cascade(pg):
    uid, lid, did = await seed(pg, amount=100)
    await launch(
        pg,
        [
            entry(target=1, rewards=[{"type": "cas", "amount": 3333}]),
            entry(code="balance-test", metric="current_balance", target=3433),
            entry(code="meta-test", metric="earned", target=2),
        ],
    )
    await tickets(pg, uid, lid, did, 1)
    await asyncio.gather(*(drain(pg, limit=10) for _ in range(4)))
    await quiet(pg)
    async with pg() as s:
        awards = list((await s.scalars(select(AchievementAward))).all())
        assert len(awards) == 3
        reward_award = next(a for a in awards if a.code == "test-purchase")

    async def repeat_reward():
        async with pg() as s, s.begin():
            await execute_rewards(s, reward_award.id, datetime.now(UTC))

    await asyncio.gather(*(repeat_reward() for _ in range(4)))
    async with pg() as s, s.begin():
        await enqueue(s, "duplicate-test", "evaluate", {}, uid)
        await enqueue(s, "duplicate-test", "evaluate", {}, uid)
    await quiet(pg)
    async with pg() as s:
        assert (await s.get(Balance, uid)).amount == 3433
        assert await s.scalar(select(func.count()).select_from(AchievementAward)) == 3
        assert (
            await s.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(
                    LedgerTransaction.user_id == uid,
                    LedgerTransaction.account_kind == LedgerAccountKind.USER_BALANCE,
                )
            )
            == 1
        )


@pytest.mark.asyncio
async def test_pg_settlement_pages_resume_and_filtered_metric_backfill(pg):
    uid, lid, did = await seed(pg)
    await launch(pg, [])
    ids = await tickets(pg, uid, lid, did, 205)
    async with pg() as s, s.begin():
        await s.execute(
            update(Ticket)
            .where(Ticket.id.in_(ids))
            .values(
                status=TicketStatus.SETTLED,
                matches=3,
                prize_amount=70,
                settled_at=datetime.now(UTC),
            )
        )
        await s.execute(
            update(Draw)
            .where(Draw.id == did)
            .values(status=DrawStatus.COMPLETED, executed_at=datetime.now(UTC))
        )
    # Simulate a crash after projection writes but before committing its cursor.
    async with pg() as s:
        e = await s.scalar(
            select(AchievementEvent).where(AchievementEvent.kind == "draw")
        )
        await AchievementProjection(s, Catalog([])).apply(e)
        await s.flush()
        await s.rollback()
    await quiet(pg)
    m = await metrics(pg, uid)
    assert m["winning_tickets"] == m["prizes_count"] == 205
    assert (
        m["won_cas"] == 14_350
        and m["profit_cas"] == 12_300
        and m["max_ticket_win"] == 70
    )
    filtered = entry(code="filter-test", metric="winning_tickets", target=205)
    # Construct a supported filter, preserving a separate threshold target.
    filtered.condition.conditions[0] = Condition(
        metric="qualifying_wins", target=205, min_prize=70
    )
    async with pg() as s, s.begin():
        await import_catalog(s, [filtered])
    await quiet(pg)
    assert (await metrics(pg, uid))[filtered.condition.conditions[0].key] == 205
    async with pg() as s:
        assert await s.scalar(select(func.count()).select_from(AchievementAward)) == 1
        event = await s.scalar(
            select(AchievementEvent).where(AchievementEvent.kind == "draw")
        )
        assert event.cursor and event.processed_at
        assert (
            await s.scalar(
                select(func.count())
                .select_from(AchievementEvent)
                .where(AchievementEvent.kind == "draw")
            )
            == 1
        )


@pytest.mark.asyncio
async def test_pg_transaction_rollback_and_failed_event_isolation(pg):
    uid, lid, did = await seed(pg)
    other, _, _ = await seed(pg)
    await launch(pg, [])
    async with pg() as s:
        await s.begin()
        await s.execute(
            insert(Ticket).values(
                id=uuid4(),
                user_id=uid,
                lottery_id=lid,
                draw_id=did,
                public_number=1,
                numbers=[1, 2, 3, 4, 5],
                purchase_price=10,
            )
        )
        await s.rollback()
    async with pg() as s:
        assert (
            await s.scalar(
                select(func.count())
                .select_from(AchievementEvent)
                .where(AchievementEvent.kind == "purchase")
            )
            == 0
        )
    async with pg() as s, s.begin():
        await enqueue(s, "bad", "unregistered", {}, uid)
        await enqueue(s, "blocked", "evaluate", {}, uid)
        await enqueue(s, "other", "evaluate", {}, other)
    await drain(pg, limit=10)
    async with pg() as s:
        events = {
            e.event_key: e for e in (await s.scalars(select(AchievementEvent))).all()
        }
        assert events["bad"].last_error == "ValueError"
        assert events["blocked"].processed_at is None
        assert events["other"].processed_at


@pytest.mark.asyncio
async def test_pg_daily_opening_dedup_catalog_validation_and_snapshots(pg):
    uid, _, _ = await seed(pg)
    await launch(pg, [entry(metric="active_days", target=2)])
    now = datetime.now(UTC)
    async with pg() as s, s.begin():
        await record_activity(s, uid, now)
        await record_activity(s, uid, now)
        await record_activity(s, uid, now + timedelta(days=1))
    await quiet(pg)
    assert (await metrics(pg, uid))["active_days"] == 2
    changed = entry(metric="active_days", target=200)
    changed.version = 2
    changed.title = "Revised fixture"
    async with pg() as s, s.begin():
        await import_catalog(s, [changed])
    async with pg() as s:
        award = await s.scalar(select(AchievementAward))
        assert (
            award.version == 1 and award.snapshot["title"] == "Temporary test fixture"
        )
    unavailable = entry(
        code="unsupported", rewards=[{"type": "cosmetic", "item": "test-only"}]
    )
    async with pg() as s:
        with pytest.raises(ValueError, match="unavailable"):
            async with s.begin():
                await import_catalog(s, [unavailable])


@pytest.mark.asyncio
async def test_pg_api_secret_ownership_and_bounded_queries(pg):
    uid, lid, did = await seed(pg)
    await launch(
        pg, [entry(target=1), entry(code="secret-test", target=999, secret=True)]
    )
    await tickets(pg, uid, lid, did, 1)
    await quiet(pg)
    app = create_app()

    async def identity():
        return CurrentMiniAppUser(uid, 123)

    async def session():
        async with pg() as s:
            yield s

    app.dependency_overrides[get_current_miniapp_user] = identity
    app.dependency_overrides[get_db_session] = session
    statements = []

    def observe(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    engine = pg.kw["bind"]
    sql_event.listen(engine.sync_engine, "before_cursor_execute", observe)
    try:
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/miniapp/achievements")
            assert response.status_code == 200
            assert len(statements) <= 4, statements
            data = response.json()
            assert data["earned"] == 1
            secret = next(item for item in data["items"] if item["secret"])
            assert set(secret) == {"code", "rarity", "secret", "status"}
            response = await client.put(
                "/api/v1/miniapp/achievements/featured", json={"codes": ["secret-test"]}
            )
            assert response.status_code == 422
            response = await client.put(
                "/api/v1/miniapp/achievements/featured",
                json={"codes": ["test-purchase"]},
            )
            assert response.status_code == 200
            response = await client.put(
                "/api/v1/miniapp/achievements/preferences",
                json={"telegram_enabled": True},
            )
            assert response.status_code == 200
    finally:
        sql_event.remove(engine.sync_engine, "before_cursor_execute", observe)


@pytest.mark.asyncio
async def test_pg_failed_grant_rolls_back_progress_and_award(pg, monkeypatch):
    from k_loto.application import achievements as module

    uid, lid, did = await seed(pg)
    await launch(pg, [entry(target=1, rewards=[{"type": "cas", "amount": 3333}])])
    await tickets(pg, uid, lid, did, 1)
    original = module.queue_award_notifications

    async def fail(*_args):
        raise RuntimeError("Injected precommit crash")

    monkeypatch.setattr(module, "queue_award_notifications", fail)
    await process_one(pg)
    async with pg() as s:
        assert await s.scalar(select(func.count()).select_from(AchievementAward)) == 0
        assert (await s.get(Balance, uid)).amount == 1_000_000
        assert (await s.get(AchievementPlayer, uid)).metrics.get("paid_tickets", 0) == 0
    monkeypatch.setattr(module, "queue_award_notifications", original)
    async with pg() as s, s.begin():
        await s.execute(
            update(AchievementEvent)
            .where(AchievementEvent.last_error.is_not(None))
            .values(available_at=datetime.now(UTC))
        )
    await quiet(pg)
    async with pg() as s:
        assert (await s.get(Balance, uid)).amount == 1_003_333
        assert await s.scalar(select(func.count()).select_from(AchievementAward)) == 1


@pytest.mark.asyncio
async def test_pg_wallet_sources_and_prelaunch_refund(pg):
    uid, lid, did = await seed(pg)
    old = (await tickets(pg, uid, lid, did, 1))[0]
    await launch(pg, [])
    new = (await tickets(pg, uid, lid, did, 1, start=2))[0]

    async def move(amount, kind, ticket_id=None):
        async with pg() as s, s.begin():
            balance = await s.scalar(
                select(Balance).where(Balance.user_id == uid).with_for_update()
            )
            before = balance.amount
            balance.amount += amount
            s.add(
                _ledger_entry(
                    operation_id=uuid4(),
                    idempotency_key=f"synthetic:{uuid4()}",
                    account_kind=LedgerAccountKind.USER_BALANCE,
                    account_id=uid,
                    transaction_type=kind,
                    before=before,
                    after=balance.amount,
                    user_id=uid,
                    ticket_id=ticket_id,
                )
            )

    await move(100, TransactionType.SYSTEM_ADJUSTMENT)
    await move(70, TransactionType.PRIZE_PAYOUT)
    await move(-10, TransactionType.TICKET_PURCHASE)
    await move(10, TransactionType.TICKET_REFUND, old)
    await move(10, TransactionType.TICKET_REFUND, new)
    await move(-50, TransactionType.ADMIN_BALANCE_ADJUSTMENT)
    await quiet(pg)
    m = await metrics(pg, uid)
    assert m["current_balance"] == 1_000_130
    assert m["received_game_cas"] == 70 and m["spent_cas"] == 0
    assert m["max_balance"] == 1_000_180


@pytest.mark.asyncio
async def test_pg_load_500_rules_10000_results_and_concurrent_reads(pg):
    uid, lid, did = await seed(pg)
    await launch(
        pg,
        [
            entry(code=f"load-{n}", metric="winning_tickets", target=n)
            for n in range(1, 501)
        ],
    )
    started = perf_counter()
    await tickets(pg, uid, lid, did, 1000)
    purchase_ms = (perf_counter() - started) * 1000
    await tickets(pg, uid, lid, did, 9000, start=1001)
    async with pg() as s:
        assert (
            await s.scalar(
                select(func.count())
                .select_from(AchievementEvent)
                .where(AchievementEvent.kind == "purchase")
            )
            == 2
        )
    async with pg() as s, s.begin():
        await s.execute(
            update(Ticket)
            .where(Ticket.draw_id == did)
            .values(
                status=TicketStatus.SETTLED,
                matches=3,
                prize_amount=70,
                settled_at=datetime.now(UTC),
            )
        )
        await s.execute(
            update(Draw)
            .where(Draw.id == did)
            .values(status=DrawStatus.COMPLETED, executed_at=datetime.now(UTC))
        )
    latencies = []

    async def reads():
        for _ in range(50):
            started = perf_counter()
            async with pg() as s:
                assert (
                    await s.scalar(select(Balance.amount).where(Balance.user_id == uid))
                    == 1_000_000
                )
            latencies.append((perf_counter() - started) * 1000)
            await asyncio.sleep(0.01)

    started = perf_counter()
    await asyncio.gather(quiet(pg), reads())
    duration = perf_counter() - started
    m = await metrics(pg, uid)
    assert m["winning_tickets"] == 10_000 and m["earned"] == 500
    async with pg() as s:
        assert await s.scalar(select(func.count()).select_from(AchievementAward)) == 500
        draw_markers = await s.scalar(
            select(func.count())
            .select_from(AchievementEvent)
            .where(AchievementEvent.kind == "draw")
        )
        assert draw_markers == 1
        pending = await s.scalar(
            select(func.count())
            .select_from(AchievementEvent)
            .where(AchievementEvent.processed_at.is_(None))
        )
        assert pending == 0
    print(
        json.dumps(
            {
                "benchmark": "achievements-local",
                "rules": 500,
                "results": 10000,
                "purchase_1000_ms": round(purchase_ms, 2),
                "drain_seconds": round(duration, 2),
                "read_samples": len(latencies),
                "read_p95_ms": round(sorted(latencies)[47], 2),
                "draw_markers": draw_markers,
                "awards": 500,
            }
        )
    )


@pytest.mark.asyncio
async def test_pg_real_purchase_service_capture_overhead(pg):
    uid, lid, did = await seed(pg)
    async with pg() as s, s.begin():
        await s.execute(
            update(Lottery)
            .where(Lottery.id == lid)
            .values(
                is_active=True, max_tickets_per_user_per_draw=10000, ticket_price=100
            )
        )
        s.add(
            JackpotAccount(
                id=uuid4(), lottery_id=lid, balance=10_000, base_amount=10_000
            )
        )
        code = await s.scalar(select(Lottery.code).where(Lottery.id == lid))
        await s.execute(
            update(Draw)
            .where(Draw.id == did)
            .values(
                configuration_snapshot={
                    "ruleset_code": "weekly_5_20",
                    "ticket_price": 100,
                }
            )
        )

    async def buy():
        started = perf_counter()
        async with pg() as s:
            await LotteryTicketPurchaseService(
                s, lottery_code=code, target_draw_id=did
            ).purchase(
                user_id=uid,
                combinations=[[1, 2, 3, 4, 5]] * 1000,
                idempotency_key=str(uuid4()),
            )
        return (perf_counter() - started) * 1000

    disabled = [await buy() for _ in range(3)]
    await launch(pg, [])
    enabled = [await buy() for _ in range(3)]
    async with pg() as s:
        assert (
            await s.scalar(
                select(func.count())
                .select_from(AchievementEvent)
                .where(AchievementEvent.kind == "purchase")
            )
            == 3
        )
        assert (
            await s.scalar(
                select(func.count())
                .select_from(AchievementEvent)
                .where(AchievementEvent.kind == "wallet")
            )
            == 3
        )
    print(
        json.dumps(
            {
                "benchmark": "real-purchase-service-1000",
                "disabled_ms": [round(x, 2) for x in disabled],
                "enabled_ms": [round(x, 2) for x in enabled],
                "events_per_purchase": 2,
            }
        )
    )
