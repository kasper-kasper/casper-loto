"""Milestone 6 administrator security, ledger and statistics tests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
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
    Balance,
    Draw,
    JackpotAccount,
    LedgerTransaction,
    Lottery,
    LotteryReserve,
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


class FakeSession:
    def __init__(
        self,
        *,
        scalar_values: list[Any],
        scalar_collections: list[list[Any]] | None = None,
        execute_rows: list[Any] | None = None,
    ) -> None:
        self.scalar_values = iter(scalar_values)
        self.scalar_collections = iter(scalar_collections or [])
        self.execute_rows = iter(execute_rows or [])
        self.added: list[Any] = []

    def begin(self) -> TransactionContext:
        return TransactionContext()

    async def scalar(self, _statement: object) -> Any:
        return next(self.scalar_values)

    async def scalars(self, _statement: object) -> ScalarCollection:
        return ScalarCollection(next(self.scalar_collections))

    async def execute(self, _statement: object) -> RowResult:
        return RowResult(next(self.execute_rows))

    def add(self, item: Any) -> None:
        self.added.append(item)


def test_admin_session_is_signed_expiring_and_contains_csrf() -> None:
    now = datetime(2026, 8, 15, 10, tzinfo=UTC)
    token, issued = issue_admin_session("owner", "s" * 48, now=now, max_age_seconds=600)

    validated = validate_admin_session(token, "s" * 48, now=now)

    assert validated.username == "owner"
    assert validated.csrf_token == issued.csrf_token
    assert validated.expires_at == now + timedelta(minutes=10)


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


async def test_daily_configuration_accepts_owner_even_ticket_price() -> None:
    lottery_id = UUID(int=35)
    lottery = Lottery(
        id=lottery_id,
        code="pll",
        name="ПЛЛ-лото",
        kind=LotteryKind.DAILY,
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

    stats = await AdminQueryService(cast(AsyncSession, fake)).number_statistics(
        lottery_id
    )

    assert [(item.number, item.appearances) for item in stats] == [
        (1, 2),
        (2, 1),
        (3, 1),
        (4, 0),
    ]
    assert stats[0].draw_percentage == 100.0
    assert stats[1].draws_since_last == 1
    assert stats[3].last_appearance is None


def test_admin_routes_cover_milestone_and_completed_draws_have_no_mutation() -> None:
    paths = create_app().openapi()["paths"]
    required = {
        "/api/v1/admin/auth/login",
        "/api/v1/admin/dashboard",
        "/api/v1/admin/players",
        "/api/v1/admin/players/{user_id}/balance-adjustments",
        "/api/v1/admin/lotteries",
        "/api/v1/admin/lotteries/{lottery_id}/configuration",
        "/api/v1/admin/lotteries/{lottery_id}/reserve-adjustments",
        "/api/v1/admin/transactions",
        "/api/v1/admin/draws",
        "/api/v1/admin/draws/{draw_id}",
        "/api/v1/admin/lotteries/{lottery_id}/number-statistics",
        "/api/v1/admin/audit",
    }
    assert required.issubset(paths)
    assert set(paths["/api/v1/admin/draws/{draw_id}"]) == {"get"}


def test_postgresql_trigger_migrations_are_asyncpg_compatible() -> None:
    """asyncpg rejects a function and trigger combined in one prepared statement."""
    migrations = Path(__file__).parents[1] / "migrations" / "versions"
    for filename in ("0001_domain_model.py", "0002_notification_outbox.py"):
        source = (migrations / filename).read_text(encoding="utf-8")
        assert "$$ LANGUAGE plpgsql;\n        CREATE TRIGGER" not in source
