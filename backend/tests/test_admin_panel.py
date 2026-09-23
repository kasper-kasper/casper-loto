"""Milestone 6 administrator security, ledger and statistics tests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.api.routes.admin import CurrentAdmin, require_admin_csrf
from k_loto.application.admin import AdminMutationService, AdminQueryService
from k_loto.core.config import Settings
from k_loto.domain.enums import DrawStatus, LotteryKind, TransactionType
from k_loto.infrastructure.admin_auth import (
    AdminSession,
    InvalidAdminSession,
    issue_admin_session,
    password_hash,
    validate_admin_session,
    verify_admin_password,
)
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    AutoPlaySetting,
    Balance,
    Draw,
    JackpotAccount,
    JackpotWinEvent,
    LedgerTransaction,
    Lottery,
    LotteryReserve,
    Ticket,
    User,
)
from k_loto.main import create_app


class TransactionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: object) -> None:
        return None


class ScalarCollection:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class RowResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def one_or_none(self) -> Any:
        return self._value

    def one(self) -> Any:
        return self._value

    def all(self) -> Any:
        return self._value

    def mappings(self) -> "RowResult":
        return self


class FakeSession:
    def __init__(
        self,
        *,
        scalar_values: list[Any],
        scalar_collections: list[list[Any]] | None = None,
        execute_rows: list[Any] | None = None,
        get_values: list[Any] | None = None,
    ) -> None:
        self.scalar_values = iter(scalar_values)
        self.scalar_collections = iter(scalar_collections or [])
        self.execute_rows = iter(execute_rows or [])
        self.get_values = iter(get_values or [])
        self.added: list[Any] = []

    def begin(self) -> TransactionContext:
        return TransactionContext()

    async def scalar(self, _statement: object) -> Any:
        return next(self.scalar_values)

    async def scalars(self, _statement: object) -> ScalarCollection:
        return ScalarCollection(next(self.scalar_collections))

    async def execute(self, _statement: object) -> RowResult:
        return RowResult(next(self.execute_rows))

    async def get(self, *_args: object, **_kwargs: object) -> Any:
        return next(self.get_values)

    def add(self, item: Any) -> None:
        self.added.append(item)


async def test_draw_detail_exposes_bingo_stage_result() -> None:
    lottery = Lottery(
        id=UUID(int=70),
        code="bingo",
        name="Kasper Bingo",
        kind=LotteryKind.DAILY,
        numbers_to_pick=12,
        max_number=60,
        ticket_price=50_000,
        timezone="Europe/Moscow",
        schedule={},
        sales_cutoff_minutes=2,
        is_active=True,
        next_draw_number=2,
        next_ticket_number=102,
    )
    draw = Draw(
        id=UUID(int=71),
        lottery_id=lottery.id,
        public_number=1,
        status=DrawStatus.COMPLETED,
        scheduled_at=datetime(2026, 9, 14, 19, tzinfo=UTC),
        sales_close_at=datetime(2026, 9, 14, 18, 58, tzinfo=UTC),
        winning_numbers=list(range(1, 59)),
        correlation_id=UUID(int=72),
        ticket_count=1,
        total_sales=50_000,
        total_payout=100_000,
        reserve_used=0,
    )
    ticket = Ticket(
        id=UUID(int=73),
        public_number=101,
        lottery_id=lottery.id,
        draw_id=draw.id,
        user_id=UUID(int=74),
        numbers=list(range(1, 13)),
        purchase_price=50_000,
        matches=12,
        prize_amount=100_000,
        bingo_result={"moves": [16, 31, 40], "amounts": [100_000, 0, 0]},
    )
    player = User(
        id=ticket.user_id,
        telegram_id=123456,
        username="winner",
        display_name="Jackpot Winner",
        is_active=True,
        is_admin=False,
    )
    fake = FakeSession(
        scalar_values=[],
        execute_rows=[(draw, lottery, None), [(ticket, player, True)]],
    )

    _, tickets = await AdminQueryService(cast(AsyncSession, fake)).draw(draw.id)

    assert tickets[0].bingo_result == {
        "moves": [16, 31, 40],
        "amounts": [100_000, 0, 0],
    }
    assert tickets[0].player_name == "Jackpot Winner"
    assert tickets[0].player_username == "winner"
    assert tickets[0].player_telegram_id == 123456
    assert tickets[0].is_jackpot_winner is True


async def test_player_ticket_history_combines_draw_and_instant_ticket_pages() -> None:
    user_id = UUID(int=900)
    ticket_id = UUID(int=901)
    lottery_id = UUID(int=902)
    purchased_at = datetime(2026, 9, 20, 12, tzinfo=UTC)
    ticket_row = {
        "id": ticket_id,
        "ticket_kind": "DRAW",
        "purchased_at": purchased_at,
        "lottery_id": lottery_id,
        "lottery_code": "weekly",
        "lottery_name": "Weekly 5/20",
        "draw_number": 7,
        "public_number": 77,
        "numbers": [1, 2, 3, 4, 5],
        "purchase_price": 100,
        "prize_amount": 250,
        "status": "SETTLED",
        "source": "MANUAL",
        "matches": 5,
        "winning_numbers": [1, 2, 3, 4, 5],
        "bingo_result": None,
    }
    fake = FakeSession(
        scalar_values=[user_id, 1],
        execute_rows=[
            [ticket_row],
            [(lottery_id, "weekly", "Weekly 5/20", 1, 0, 1, 100, 250)],
            (0, 0, 0, 0),
        ],
    )

    history, total, stats = await AdminQueryService(
        cast(AsyncSession, fake)
    ).player_ticket_history(user_id, history_filter="wins", limit=1, offset=0)

    assert total == 1
    assert history[0].id == ticket_id
    assert history[0].numbers == (1, 2, 3, 4, 5)
    assert history[0].prize_amount == 250
    assert stats[0].lottery_code == "weekly"
    assert stats[0].ticket_count == 1
    assert stats[-1].lottery_code == "kasper-live"


def test_admin_session_is_signed_expiring_and_contains_csrf() -> None:
    now = datetime(2026, 8, 15, 10, tzinfo=UTC)
    token, issued = issue_admin_session(
        "owner", "s" * 48, now=now, max_age_seconds=600, remembered=True
    )

    validated = validate_admin_session(token, "s" * 48, now=now)

    assert validated.username == "owner"
    assert validated.csrf_token == issued.csrf_token
    assert validated.expires_at == now + timedelta(minutes=10)
    assert validated.remembered is True


def test_tampered_and_expired_admin_sessions_are_rejected() -> None:
    now = datetime(2026, 8, 15, 10, tzinfo=UTC)
    token, _ = issue_admin_session("owner", "s" * 48, now=now, max_age_seconds=1)

    with pytest.raises(InvalidAdminSession, match="signature"):
        validate_admin_session(token + "x", "s" * 48, now=now)
    with pytest.raises(InvalidAdminSession, match="expired"):
        validate_admin_session(token, "s" * 48, now=now + timedelta(seconds=2))


def test_argon2_password_verification() -> None:
    encoded = password_hash.hash("a strong administrator password")

    assert verify_admin_password("a strong administrator password", encoded)
    assert not verify_admin_password("wrong", encoded)
    assert not verify_admin_password("password", "malformed")


def test_incomplete_admin_configuration_is_disabled() -> None:
    base = {
        "database_url": "postgresql+asyncpg://test:test@localhost/test",
        "admin_secret": None,
        "admin_username": None,
        "admin_password_hash": None,
    }

    assert not Settings(**base).admin_auth_available
    assert not Settings(
        **{
            **base,
            "admin_secret": "short",
            "admin_username": "owner",
            "admin_password_hash": "hash",
        }
    ).admin_auth_available
    assert Settings(
        **{
            **base,
            "admin_secret": "s" * 48,
            "admin_username": "owner",
            "admin_password_hash": "hash",
        }
    ).admin_auth_available


async def test_admin_mutations_require_matching_csrf_token() -> None:
    session = AdminSession("owner", "expected-csrf", datetime(2026, 8, 16, tzinfo=UTC))
    admin = CurrentAdmin(UUID(int=1), session)

    assert await require_admin_csrf(admin, "expected-csrf") is admin
    with pytest.raises(HTTPException) as rejected:
        await require_admin_csrf(admin, "wrong-csrf")
    assert rejected.value.status_code == 403


async def test_balance_adjustment_is_ledgered_audited_and_idempotent() -> None:
    user_id = UUID(int=10)
    admin_id = UUID(int=20)
    balance = Balance(user_id=user_id, amount=500, version=1)
    fake = FakeSession(scalar_values=[None, balance])
    service = AdminMutationService(cast(AsyncSession, fake), admin_id)

    result = await service.set_user_balance(
        user_id,
        target_amount=900,
        reason="Owner test allocation",
        idempotency_key="balance-1",
    )

    ledger = next(item for item in fake.added if isinstance(item, LedgerTransaction))
    audit = next(item for item in fake.added if isinstance(item, AdminAuditLog))
    assert result.amount == 900
    assert balance.amount == 900
    assert ledger.type == TransactionType.ADMIN_BALANCE_ADJUSTMENT
    assert (ledger.balance_before, ledger.amount, ledger.balance_after) == (
        500,
        400,
        900,
    )
    assert audit.old_values == {"amount": 500}
    assert audit.new_values == {"amount": 900}

    retry_fake = FakeSession(scalar_values=[ledger])
    retry = await AdminMutationService(
        cast(AsyncSession, retry_fake), admin_id
    ).set_user_balance(
        user_id,
        target_amount=900,
        reason="Owner test allocation",
        idempotency_key="balance-1",
    )
    assert retry.already_processed
    assert retry_fake.added == []


async def test_reserve_adjustment_is_ledgered_and_never_negative() -> None:
    lottery_id = UUID(int=30)
    reserve = LotteryReserve(
        id=UUID(int=31), lottery_id=lottery_id, balance=100, version=1
    )
    fake = FakeSession(scalar_values=[None, reserve])
    service = AdminMutationService(cast(AsyncSession, fake), UUID(int=20))

    result = await service.set_reserve(
        lottery_id,
        target_amount=1_000,
        reason="Increase Weekly guarantee",
        idempotency_key="reserve-1",
    )

    ledger = next(item for item in fake.added if isinstance(item, LedgerTransaction))
    assert result.amount == 1_000
    assert ledger.type == TransactionType.RESERVE_ADJUSTMENT
    assert ledger.amount == 900
    with pytest.raises(ValueError, match="negative"):
        await service.set_reserve(
            lottery_id,
            target_amount=-1,
            reason="Invalid",
            idempotency_key="reserve-2",
        )


async def test_current_jackpot_adjustment_is_ledgered_and_audited() -> None:
    lottery_id = UUID(int=32)
    jackpot = JackpotAccount(
        id=UUID(int=320),
        lottery_id=lottery_id,
        balance=888_888,
        base_amount=888_888,
        version=1,
    )
    fake = FakeSession(scalar_values=[None, jackpot])

    result = await AdminMutationService(
        cast(AsyncSession, fake), UUID(int=20)
    ).set_jackpot(
        lottery_id,
        target_amount=999_999,
        reason="Owner changed the current Fast jackpot",
        idempotency_key="jackpot-1",
    )

    ledger = next(item for item in fake.added if isinstance(item, LedgerTransaction))
    audit = next(item for item in fake.added if isinstance(item, AdminAuditLog))
    assert result.amount == 999_999
    assert jackpot.balance == 999_999
    assert ledger.account_kind.value == "JACKPOT"
    assert ledger.type == TransactionType.SYSTEM_ADJUSTMENT
    assert (ledger.balance_before, ledger.amount, ledger.balance_after) == (
        888_888,
        111_111,
        999_999,
    )
    assert audit.entity_type == "jackpot_account"


async def test_auto_play_is_owner_audited_and_limited_to_five_tickets() -> None:
    user_id = UUID(int=33)
    user = User(
        id=user_id,
        telegram_id=1201541335,
        display_name="Owner player",
        is_admin=False,
        is_active=True,
    )
    fake = FakeSession(scalar_values=[user], get_values=[None])

    setting = await AdminMutationService(
        cast(AsyncSession, fake), UUID(int=20)
    ).set_auto_play(
        user_id,
        enabled=True,
        tickets_per_draw=5,
        reason="Owner requested five tickets per draw",
    )

    assert setting.enabled
    assert setting.tickets_per_draw == 5
    assert any(isinstance(item, AutoPlaySetting) for item in fake.added)
    audit = next(item for item in fake.added if isinstance(item, AdminAuditLog))
    assert audit.entity_type == "auto_play_setting"
    assert audit.new_values == {"enabled": True, "tickets_per_draw": 5}

    with pytest.raises(ValueError, match="between 1 and 5"):
        await AdminMutationService(
            cast(AsyncSession, fake), UUID(int=20)
        ).set_auto_play(
            user_id,
            enabled=True,
            tickets_per_draw=6,
            reason="Invalid amount",
        )


async def test_daily_configuration_accepts_owner_even_ticket_price() -> None:
    lottery_id = UUID(int=35)
    lottery = Lottery(
        id=lottery_id,
        code="pll",
        name="ПЛЛ-лото",
        kind=LotteryKind.DAILY,
        ruleset_code="daily_4_15",
        numbers_to_pick=4,
        max_number=15,
        ticket_price=20_000,
        timezone="Europe/Moscow",
        schedule={"draw_time": "02:22"},
        sales_cutoff_minutes=2,
        is_active=True,
        next_draw_number=2,
        next_ticket_number=1,
    )
    jackpot = JackpotAccount(
        id=UUID(int=36),
        lottery_id=lottery_id,
        balance=1_000,
        base_amount=1_000,
        version=1,
    )
    fake = FakeSession(
        scalar_values=[lottery, jackpot, None],
        execute_rows=[(lottery, jackpot, None, None)],
    )

    result = await AdminMutationService(
        cast(AsyncSession, fake), UUID(int=20)
    ).configure_lottery(
        lottery_id,
        ticket_price=22_222,
        base_jackpot=2_811_996,
        reason="Owner-approved PLL configuration",
    )

    assert result.ticket_price == 22_222
    assert result.base_jackpot == 2_811_996
    assert jackpot.base_amount == 2_811_996


async def test_number_statistics_are_derived_from_completed_draw_history() -> None:
    lottery_id = UUID(int=40)
    lottery = Lottery(
        id=lottery_id,
        code="weekly",
        name="Weekly",
        kind=LotteryKind.WEEKLY,
        numbers_to_pick=2,
        max_number=4,
        ticket_price=100,
        timezone="Europe/Moscow",
        schedule={},
        sales_cutoff_minutes=5,
        is_active=True,
        next_draw_number=3,
        next_ticket_number=1,
    )
    first = Draw(
        id=UUID(int=41),
        lottery_id=lottery_id,
        public_number=1,
        status=DrawStatus.COMPLETED,
        scheduled_at=datetime(2026, 8, 1, tzinfo=UTC),
        sales_close_at=datetime(2026, 8, 1, tzinfo=UTC),
        winning_numbers=[1, 2],
        correlation_id=UUID(int=42),
        ticket_count=0,
        total_sales=0,
        total_payout=0,
        reserve_used=0,
    )
    second = Draw(
        id=UUID(int=43),
        lottery_id=lottery_id,
        public_number=2,
        status=DrawStatus.COMPLETED,
        scheduled_at=datetime(2026, 8, 8, tzinfo=UTC),
        sales_close_at=datetime(2026, 8, 8, tzinfo=UTC),
        winning_numbers=[1, 3],
        correlation_id=UUID(int=44),
        ticket_count=0,
        total_sales=0,
        total_payout=0,
        reserve_used=0,
    )
    fake = FakeSession(scalar_values=[lottery], scalar_collections=[[first, second]])

    report = await AdminQueryService(cast(AsyncSession, fake)).number_statistics(
        lottery_id
    )
    stats = report.numbers

    assert report.draw_count == 2
    assert report.window_size == 20
    assert [(item.number, item.appearances) for item in stats] == [
        (1, 2),
        (2, 1),
        (3, 1),
        (4, 0),
    ]
    assert stats[0].draw_percentage == 100.0
    assert stats[1].draws_since_last == 1
    assert stats[3].last_appearance is None


async def test_daily_schedule_returns_moscow_day_in_chronological_order() -> None:
    lottery = Lottery(
        id=UUID(int=45),
        code="pll",
        name="ПЛЛ-лото",
        kind=LotteryKind.DAILY,
        ruleset_code="daily_4_15",
        numbers_to_pick=4,
        max_number=15,
        ticket_price=24_000,
        timezone="Europe/Moscow",
        schedule={"slots": ["02:22", "13:45"]},
        sales_cutoff_minutes=2,
        is_active=True,
        next_draw_number=3,
        next_ticket_number=1,
    )
    first = Draw(
        id=UUID(int=46),
        lottery_id=lottery.id,
        public_number=1,
        status=DrawStatus.COMPLETED,
        scheduled_at=datetime(2026, 9, 1, 23, 22, tzinfo=UTC),
        sales_close_at=datetime(2026, 9, 1, 23, 20, tzinfo=UTC),
        correlation_id=UUID(int=47),
        ticket_count=0,
        total_sales=0,
        total_payout=0,
        reserve_used=0,
    )
    second = Draw(
        id=UUID(int=48),
        lottery_id=lottery.id,
        public_number=2,
        status=DrawStatus.SCHEDULED,
        scheduled_at=datetime(2026, 9, 2, 10, 45, tzinfo=UTC),
        sales_close_at=datetime(2026, 9, 2, 10, 43, tzinfo=UTC),
        correlation_id=UUID(int=49),
        ticket_count=0,
        total_sales=0,
        total_payout=0,
        reserve_used=0,
    )
    fake = FakeSession(
        scalar_values=[], execute_rows=[[(first, lottery), (second, lottery)]]
    )

    rows = await AdminQueryService(cast(AsyncSession, fake)).daily_schedule(
        now=datetime(2026, 9, 2, 9, tzinfo=UTC)
    )

    assert [(row.public_number, row.lottery_name) for row in rows] == [
        (1, "ПЛЛ-лото"),
        (2, "ПЛЛ-лото"),
    ]


async def test_daily_schedule_projects_fast_rounds_without_creating_draws() -> None:
    lottery = Lottery(
        id=UUID(int=60),
        code="flash",
        name="FLASH",
        kind=LotteryKind.DAILY,
        ruleset_code="fast_3_15",
        numbers_to_pick=3,
        max_number=15,
        ticket_price=888,
        timezone="Europe/Moscow",
        schedule={
            "type": "interval",
            "interval_minutes": 20,
            "anchor_time": "00:00",
        },
        sales_cutoff_minutes=1,
        is_active=True,
        next_draw_number=2,
        next_ticket_number=1,
    )
    first = Draw(
        id=UUID(int=61),
        lottery_id=lottery.id,
        public_number=1,
        status=DrawStatus.COMPLETED,
        scheduled_at=datetime(2026, 9, 1, 21, 0, tzinfo=UTC),
        sales_close_at=datetime(2026, 9, 1, 20, 59, tzinfo=UTC),
        correlation_id=UUID(int=62),
        ticket_count=0,
        total_sales=0,
        total_payout=0,
        reserve_used=0,
    )
    fake = FakeSession(scalar_values=[], execute_rows=[[(first, lottery)]])

    rows = await AdminQueryService(cast(AsyncSession, fake)).daily_schedule(
        now=datetime(2026, 9, 2, 9, tzinfo=UTC)
    )

    assert len(rows) == 72
    assert rows[0].public_number == 1
    assert rows[-1].public_number == 72
    assert rows[-1].scheduled_at == datetime(2026, 9, 2, 20, 40, tzinfo=UTC)
    assert fake.added == []


async def test_ticket_analytics_uses_aggregate_rows() -> None:
    lottery_id = UUID(int=50)
    fake = FakeSession(
        scalar_values=[],
        execute_rows=[
            [(100, 10, 90, 21, 8, 5, 10_000, 2_500)],
            [(lottery_id, "Weekly", True, 100, 10, 90, 21, 8, 5, 10_000, 2_500)],
        ],
    )

    analytics = await AdminQueryService(cast(AsyncSession, fake)).ticket_analytics()

    assert analytics.overall.total_tickets == 100
    assert analytics.overall.winning_tickets == 21
    assert analytics.lotteries[0].lottery_name == "Weekly"
    assert analytics.lotteries[0].total_payout == 2_500


async def test_dashboard_activity_uses_compact_draw_buckets() -> None:
    bucket = datetime(2026, 9, 4, 16, tzinfo=UTC)
    fake = FakeSession(
        scalar_values=[],
        execute_rows=[[(bucket, 15, 13_320, 1_020_156)]],
    )

    points = await AdminQueryService(cast(AsyncSession, fake)).activity(period_days=1)

    assert points[0].bucket_at == bucket
    assert points[0].ticket_count == 15
    assert points[0].total_sales == 13_320
    assert points[0].total_payout == 1_020_156


def test_admin_routes_cover_milestone_and_completed_draws_have_no_mutation() -> None:
    paths = create_app().openapi()["paths"]
    required = {
        "/api/v1/admin/auth/login",
        "/api/v1/admin/dashboard",
        "/api/v1/admin/kasper-live",
        "/api/v1/admin/players",
        "/api/v1/admin/players/{user_id}/balance-adjustments",
        "/api/v1/admin/lotteries",
        "/api/v1/admin/lotteries/{lottery_id}/configuration",
        "/api/v1/admin/lotteries/{lottery_id}/jackpot-adjustments",
        "/api/v1/admin/lotteries/{lottery_id}/reserve-adjustments",
        "/api/v1/admin/transactions",
        "/api/v1/admin/draws",
        "/api/v1/admin/schedule",
        "/api/v1/admin/draws/{draw_id}",
        "/api/v1/admin/lotteries/{lottery_id}/number-statistics",
        "/api/v1/admin/ticket-analytics",
        "/api/v1/admin/activity",
        "/api/v1/admin/audit",
        "/api/v1/admin/interesting-facts",
        "/api/v1/admin/interesting-facts/{fact_id}/status",
        "/api/v1/admin/release-notes/{kind}",
    }
    assert required.issubset(paths)
    assert set(paths["/api/v1/admin/draws/{draw_id}"]) == {"get"}
    assert set(paths["/api/v1/admin/interesting-facts/{fact_id}/status"]) == {"patch"}


def test_postgresql_trigger_migrations_are_asyncpg_compatible() -> None:
    """asyncpg rejects a function and trigger combined in one prepared statement."""
    migrations = Path(__file__).parents[1] / "migrations" / "versions"
    for filename in ("0001_domain_model.py", "0002_notification_outbox.py"):
        source = (migrations / filename).read_text(encoding="utf-8")
        assert "$$ LANGUAGE plpgsql;\n        CREATE TRIGGER" not in source


def test_alembic_revision_ids_fit_the_version_table() -> None:
    migrations = Path(__file__).parents[1] / "migrations" / "versions"
    for path in migrations.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.startswith("revision: str = "):
                revision = line.split('"')[1]
                assert len(revision) <= 32, path.name


async def test_jackpot_totals_and_latest_ignore_history_limit() -> None:
    now = datetime(2026, 9, 5, tzinfo=UTC)
    shadow_id, flash_id, empty_id = UUID(int=301), UUID(int=302), UUID(int=303)
    shadow = Lottery(id=shadow_id, code="shadow", name="SHADOW", is_active=True)
    recent = JackpotWinEvent(
        id=UUID(int=401),
        lottery_id=shadow_id,
        draw_id=UUID(int=501),
        jackpot_amount=100,
        winner_ticket_count=2,
        winner_user_count=1,
        base_jackpot_after=1_000,
        occurred_at=now,
    )
    archived = JackpotWinEvent(
        id=UUID(int=402),
        lottery_id=flash_id,
        draw_id=UUID(int=502),
        jackpot_amount=900,
        winner_ticket_count=1,
        winner_user_count=1,
        base_jackpot_after=1_000,
        occurred_at=now - timedelta(days=1),
    )
    fake = FakeSession(
        scalar_values=[None],
        execute_rows=[
            [(recent, shadow, 25)],
            (7, 20_000, 8_800),
            [
                (shadow_id, "shadow", "SHADOW", True, 5, 15_000, now, 8_800),
                (
                    flash_id,
                    "flash",
                    "FLASH",
                    False,
                    2,
                    5_000,
                    archived.occurred_at,
                    4_100,
                ),
                (empty_id, "pll", "PLL", True, 0, 0, None, 0),
            ],
            [(recent, 25), (archived, 12)],
        ],
    )
    report = await AdminQueryService(cast(AsyncSession, fake)).jackpot_analytics()
    assert report["total_wins"] == 7
    assert report["total_paid"] == 20_000
    assert report["largest_win"] == 8_800
    assert len(report["history"]) == 1
    assert report["last_win"]["jackpot_amount"] == 100
    assert report["last_win"]["winner_ticket_count"] == 2
    assert report["last_win"]["draw_number"] == 25
    by_code = {row["code"]: row for row in report["lotteries"]}
    assert by_code["shadow"]["largest_win"] == 8_800
    assert by_code["flash"]["is_active"] is False
    assert by_code["flash"]["last_win_amount"] == 900
    assert by_code["flash"]["last_draw_number"] == 12
    assert by_code["pll"]["last_win_amount"] is None
    assert sum(row["win_count"] for row in by_code.values()) == report["total_wins"]


async def test_jackpot_empty_history_has_no_invented_last_win() -> None:
    fake = FakeSession(scalar_values=[None], execute_rows=[[], (0, 0, 0), [], []])
    report = await AdminQueryService(cast(AsyncSession, fake)).jackpot_analytics()
    assert report["last_win"] is None
    assert report["total_wins"] == report["total_paid"] == 0


async def test_jackpot_catalog_returns_draw_links_and_winner_counts() -> None:
    occurred_at = datetime(2026, 9, 19, 12, tzinfo=UTC)
    event = SimpleNamespace(
        id=UUID(int=801),
        draw_id=UUID(int=802),
        jackpot_amount=25_000,
        winner_ticket_count=2,
        winner_user_count=1,
        base_jackpot_after=1_000,
        occurred_at=occurred_at,
    )
    lottery = SimpleNamespace(code="flash", name="FLASH")
    fake = FakeSession(scalar_values=[], execute_rows=[[(event, lottery, 411)]])

    rows = await AdminQueryService(
        cast(AsyncSession, fake), scope="fast"
    ).jackpot_events(limit=100, offset=0)

    assert rows == (
        {
            "id": event.id,
            "lottery_code": "flash",
            "lottery_name": "FLASH",
            "draw_id": event.draw_id,
            "draw_number": 411,
            "jackpot_amount": 25_000,
            "winner_ticket_count": 2,
            "winner_user_count": 1,
            "base_jackpot_after": 1_000,
            "occurred_at": occurred_at,
        },
    )


async def test_archive_draw_query_includes_previous_format_metadata() -> None:
    scheduled_at = datetime(2026, 9, 19, 12, tzinfo=UTC)
    draw = SimpleNamespace(
        id=UUID(int=901),
        lottery_id=UUID(int=902),
        public_number=411,
        status=DrawStatus.COMPLETED,
        scheduled_at=scheduled_at,
        sales_close_at=scheduled_at,
        executed_at=scheduled_at,
        winning_numbers=[1, 2, 3],
        ticket_count=5,
        total_sales=500,
        total_payout=2_500,
        jackpot_opening=2_000,
        jackpot_closing=0,
        distribution_opening=0,
        distribution_closing=0,
        reserve_used=0,
        kasper_fund_used=0,
        correlation_id=UUID(int=903),
        configuration_snapshot={"ruleset_code": "flash-legacy"},
    )
    lottery = SimpleNamespace(id=draw.lottery_id, code="flash", name="FLASH")
    fake = FakeSession(scalar_values=[], execute_rows=[[(draw, lottery)]])

    rows = await AdminQueryService(cast(AsyncSession, fake), scope="fast").draws(
        period="archived"
    )

    assert len(rows) == 1
    assert rows[0].id == draw.id
    assert rows[0].ruleset_code == "flash-legacy"
