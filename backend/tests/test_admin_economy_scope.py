"""Exercise Admin period filters on actual rows, including aggregate queries."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, aliased

from k_loto.application.admin import AdminQueryService
from k_loto.application.economy_archive import apply_archive_scope
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    Draw,
    InstantTicket,
    JackpotWinEvent,
    LedgerTransaction,
    NotificationOutbox,
    Publication,
    Ticket,
)

START = datetime(2026, 10, 18, 0, tzinfo=UTC)
DATED_MODELS = (
    (InstantTicket, "purchased_at"),
    (LedgerTransaction, "created_at"),
    (JackpotWinEvent, "occurred_at"),
    (AdminAuditLog, "created_at"),
    (NotificationOutbox, "created_at"),
    (Publication, "created_at"),
)


class ReadSession:
    def __init__(self, session):
        self.sync_session = session
        self.info = session.info

    async def execute(self, statement):
        return self.sync_session.execute(statement)


@pytest.fixture
def history():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE lotteries (id TEXT, name TEXT, code TEXT, "
                "is_active BOOLEAN, ruleset_code TEXT)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE draws (id TEXT, lottery_id TEXT, "
                "configuration_snapshot JSON)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE tickets (id TEXT, draw_id TEXT, lottery_id TEXT, "
                "user_id TEXT, status TEXT, purchase_price INTEGER, "
                "prize_amount INTEGER)"
            )
        )
        conn.execute(
            text("INSERT INTO lotteries VALUES (:id, 'Test', 'pll', 1, 'new')"),
            {"id": UUID(int=1).hex},
        )
        for model, column in DATED_MODELS:
            conn.execute(
                text(f"CREATE TABLE {model.__tablename__} (id TEXT, {column} DATETIME)")
            )

    def seed(number, epoch, at):
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO draws VALUES (:id, :lottery, :snapshot)"),
                {
                    "id": UUID(int=number).hex,
                    "lottery": UUID(int=1).hex,
                    "snapshot": "{}" if epoch == 1 else '{"economy_epoch": 2}',
                },
            )
            conn.execute(
                text(
                    "INSERT INTO tickets VALUES "
                    "(:id, :id, :lottery, :user, 'SETTLED', 100, :prize)"
                ),
                {
                    "id": UUID(int=number).hex,
                    "lottery": UUID(int=1).hex,
                    "user": UUID(int=2).hex,
                    "prize": 500 if epoch == 1 else 900,
                },
            )
            for model, _column in DATED_MODELS:
                conn.execute(
                    text(f"INSERT INTO {model.__tablename__} VALUES (:id, :at)"),
                    {
                        "id": UUID(int=number).hex,
                        "at": at.strftime("%Y-%m-%d %H:%M:%S.%f"),
                    },
                )

    seed(10, 1, START - timedelta(seconds=1))
    yield engine, seed
    engine.dispose()


@pytest.mark.parametrize("new_rows", [False, True])
async def test_all_admin_statistics_start_empty_and_archive_stays_separate(
    history, new_rows
):
    engine, seed = history
    if new_rows:
        seed(20, 2, START)
    for archive in (False, True):
        with Session(engine) as sync:
            session = ReadSession(sync)
            apply_archive_scope(
                cast(AsyncSession, session), epoch=2, started_at=START, archive=archive
            )
            expected = 1 if archive or new_rows else 0
            for model in (Draw, Ticket, *(model for model, _ in DATED_MODELS)):
                assert sync.scalar(select(func.count(model.id))) == expected, model
            ticket_alias = aliased(Ticket)
            assert sync.scalar(select(func.count(ticket_alias.id))) == expected
            report = await AdminQueryService(
                cast(AsyncSession, session)
            ).ticket_analytics()
            assert report.overall.total_tickets == expected
            assert report.overall.winning_tickets == expected
            assert report.overall.total_payout == expected * (500 if archive else 900)
            # The empty current epoch still lists the lottery with zero aggregates.
            assert len(report.lotteries) == 1
            assert report.lotteries[0].total_tickets == expected
    with Session(engine) as sync:
        assert sync.scalar(select(func.count(Ticket.id))) == 1 + int(new_rows)


async def test_business_overview_does_not_query_technical_tables():
    result = SimpleNamespace(all=lambda: [])
    session = SimpleNamespace(execute=AsyncMock(return_value=result))
    service = AdminQueryService(cast(AsyncSession, session))
    service.today_summary = AsyncMock(return_value={"purchased_tickets": 0})
    report = await service.operational_status(technical=False)
    assert report == {"today": {"purchased_tickets": 0}, "next_draws": []}
    assert session.execute.await_count == 1
    query = str(session.execute.call_args.args[0])
    assert "scheduler" not in query and "notification" not in query


async def test_archive_number_statistics_resolve_the_old_payout_version():
    lottery = SimpleNamespace(
        id=UUID(int=1), name="2:22", ruleset_code="pll_4_15_economy_v2", max_number=15
    )
    draw = SimpleNamespace(
        winning_numbers=[1, 2, 3, 4], scheduled_at=START - timedelta(days=1)
    )
    session = SimpleNamespace(
        info={"economy_scope": (2, "archive")},
        scalar=AsyncMock(side_effect=[lottery, "daily_4_15"]),
        scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [draw])),
    )
    report = await AdminQueryService(cast(AsyncSession, session)).number_statistics(
        lottery.id
    )
    assert report.draw_count == 1 and len(report.numbers) == 15
    assert report.numbers[0].appearances == 1
    parameters = session.scalars.call_args.args[0].compile().params.values()
    assert "daily_4_15" in parameters
    assert "pll_4_15_economy_v2" not in parameters
