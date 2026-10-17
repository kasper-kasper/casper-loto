"""Execute the ledger query against real rows, including midnight/epoch transfers."""

from datetime import UTC, date, datetime
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.economy_reporting import EconomyReportService, daily_flows_query
from k_loto.domain.enums import LedgerAccountKind as Account
from k_loto.domain.enums import TransactionType as Kind


@pytest.fixture
def ledger():
    engine = create_engine("sqlite://")
    metadata = MetaData()
    table = Table(
        "ledger_transactions",
        metadata,
        Column("operation_id", String),
        Column("created_at", DateTime),
        Column("amount", Integer),
        Column("account_kind", String),
        Column("type", String),
    )
    metadata.create_all(engine)
    with engine.connect() as connection:

        def timezone(zone, value):
            from zoneinfo import ZoneInfo

            return (
                datetime.fromisoformat(value)
                .replace(tzinfo=UTC)
                .astimezone(ZoneInfo(zone))
                .replace(tzinfo=None)
                .isoformat()
            )

        connection.connection.driver_connection.create_function("timezone", 2, timezone)

        def operation(at, entries):
            key = uuid4().hex
            connection.execute(
                table.insert(),
                [
                    dict(
                        operation_id=key,
                        created_at=stamp or at,
                        account_kind=account,
                        type=kind,
                        amount=amount,
                    )
                    for account, kind, amount, stamp in entries
                ],
            )

        yield connection, table, operation
    engine.dispose()


def utc(value):
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def rows(connection, table, *, epoch=None, archive=False):
    return (
        connection.execute(
            daily_flows_query(
                table,
                start=utc("2026-10-16T21:00:00"),
                end=utc("2026-10-18T21:00:00"),
                epoch_started=epoch,
                archive=archive,
            )
        )
        .mappings()
        .all()
    )


def test_all_games_grants_refunds_and_transfers_are_counted_once(ledger):
    connection, table, operation = ledger
    before = utc("2026-10-17T20:59:59")
    after = utc("2026-10-17T21:00:00")

    def add(entries, at=after):
        operation(at, [(*entry, None) for entry in entries])

    add([(Account.USER_BALANCE, Kind.SYSTEM_ADJUSTMENT, 100_000)], before)
    add(
        [
            (Account.USER_BALANCE, Kind.TICKET_PURCHASE, -2000),
            (Account.JACKPOT, Kind.TICKET_PURCHASE, 800),
        ]
    )
    add(
        [
            (Account.USER_BALANCE, Kind.PRIZE_PAYOUT, 5000),
            (Account.KASPER_FUND, Kind.PRIZE_PAYOUT, -5000),
        ]
    )
    add(
        [
            (Account.USER_BALANCE, Kind.TICKET_REFUND, 2000),
            (Account.JACKPOT, Kind.TICKET_REFUND, -2000),
        ]
    )
    add([(Account.USER_BALANCE, Kind.ADMIN_BALANCE_ADJUSTMENT, 300)])
    add([(Account.USER_BALANCE, Kind.ADMIN_BALANCE_ADJUSTMENT, -100)])
    add([(Account.USER_BALANCE, Kind.SYSTEM_ADJUSTMENT, -500)])
    add([(Account.USER_BALANCE, Kind.SYSTEM_ADJUSTMENT, 200)])
    add(
        [
            (Account.USER_BALANCE, Kind.TICKET_PURCHASE, -1000),
            (Account.JACKPOT, Kind.TICKET_PURCHASE, 1000),
        ]
    )
    add(
        [
            (Account.KASPER_FUND, Kind.SYSTEM_ADJUSTMENT, -10_000),
            (Account.JACKPOT, Kind.SYSTEM_ADJUSTMENT, 10_000),
        ]
    )
    operation(
        before,
        [
            (Account.KASPER_FUND, Kind.PRIZE_PAYOUT, -700, before),
            (Account.USER_BALANCE, Kind.PRIZE_PAYOUT, 700, utc("2026-10-17T21:00:01")),
        ],
    )
    previous, today = rows(connection, table)
    assert previous["day"] == "2026-10-17"
    assert previous["credited"] == 100_700 and previous["issued"] == 100_000
    assert today["day"] == "2026-10-18"
    assert dict(today) == dict(
        day="2026-10-18",
        credited=7500,
        debited=3600,
        prizes=5000,
        refunds=2000,
        admin_credit=300,
        admin_debit=100,
        purchases=3000,
        issued=500,
        burned=1800,
    )


def test_epoch_boundary_never_splits_a_transfer_into_issuance(ledger):
    connection, table, operation = ledger
    cutoff = utc("2026-10-17T21:30:00")
    operation(
        cutoff,
        [
            (Account.KASPER_FUND, Kind.PRIZE_PAYOUT, -40, utc("2026-10-17T21:29:59")),
            (Account.USER_BALANCE, Kind.PRIZE_PAYOUT, 40, utc("2026-10-17T21:30:01")),
        ],
    )
    operation(
        utc("2026-10-17T21:40:00"),
        [(Account.USER_BALANCE, Kind.SYSTEM_ADJUSTMENT, 50, None)],
    )
    current = rows(connection, table, epoch=cutoff)[0]
    archive = rows(connection, table, epoch=cutoff, archive=True)[0]
    assert current["credited"] == current["issued"] == 50
    assert archive["credited"] == 40 and archive["issued"] == archive["burned"] == 0


async def test_report_marks_partial_and_excluded_days_without_fake_comparisons():
    from unittest.mock import MagicMock

    session = MagicMock()
    session.info = {
        "economy_scope": (2, "current"),
        "economy_started_at": utc("2026-10-17T21:30:00"),
    }

    async def execute(_query):
        result = MagicMock()
        result.mappings.return_value.all.return_value = []
        return result

    session.execute = execute
    report = await EconomyReportService(cast(AsyncSession, session)).daily(
        now=utc("2026-10-18T12:00:00")
    )
    assert len(report["days"]) == 7
    assert report["days"][-1]["partial"] is True
    assert report["days"][-1]["included"] is True
    assert report["days"][-2]["included"] is False
    assert report["days"][-1]["player_net"] == 0
    with pytest.raises(ValueError):
        await EconomyReportService(cast(AsyncSession, session)).daily(
            through=date(2027, 1, 1), now=utc("2026-10-18T12:00:00")
        )


def test_admin_report_accepts_integer_query_parameters(monkeypatch):
    from fastapi.testclient import TestClient

    from k_loto.api.dependencies import get_db_session
    from k_loto.api.routes.admin import get_current_admin
    from k_loto.main import create_app

    recorded = []

    async def daily(self, *, days, through):
        recorded.append((days, through))
        return {"days": []}

    monkeypatch.setattr(EconomyReportService, "daily", daily)
    app = create_app()
    app.dependency_overrides[get_current_admin] = lambda: object()

    async def fake_session():
        yield object()

    app.dependency_overrides[get_db_session] = fake_session
    response = TestClient(app).get("/api/v1/admin/economy?days=30&through=2026-10-17")
    assert response.status_code == 200
    assert recorded == [(30, date(2026, 10, 17))]
