"""One-time Telegram-to-Web login service tests."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.web_login import TelegramWebLoginService
from k_loto.infrastructure.database.models import User, WebLoginToken


class TransactionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeSession:
    def __init__(self, scalar_values: list[Any]) -> None:
        self.scalar_values = iter(scalar_values)
        self.added: list[Any] = []

    def begin(self) -> TransactionContext:
        return TransactionContext()

    async def scalar(self, _statement: object) -> Any:
        return next(self.scalar_values)

    def add(self, item: Any) -> None:
        self.added.append(item)


def player() -> User:
    return User(
        id=UUID(int=10),
        telegram_id=123,
        username="player",
        display_name="Player",
        is_active=True,
        is_admin=False,
    )


async def test_issue_stores_only_hash_and_five_minute_expiry() -> None:
    now = datetime(2026, 8, 15, 12, tzinfo=UTC)
    fake = FakeSession([player()])

    issued = await TelegramWebLoginService(cast(AsyncSession, fake)).issue(
        123, now=now, max_age_seconds=300
    )

    record = next(item for item in fake.added if isinstance(item, WebLoginToken))
    assert len(issued.token) >= 32
    assert record.token_hash != issued.token
    assert len(record.token_hash) == 64
    assert issued.expires_at == now + timedelta(minutes=5)


async def test_consume_is_atomic_and_one_time() -> None:
    now = datetime(2026, 8, 15, 12, tzinfo=UTC)
    record = WebLoginToken(
        id=UUID(int=11),
        user_id=UUID(int=10),
        token_hash="a" * 64,
        expires_at=now + timedelta(minutes=1),
        used_at=None,
    )
    fake = FakeSession([record, player()])

    result = await TelegramWebLoginService(cast(AsyncSession, fake)).consume(
        "x" * 32, now=now
    )

    assert result is not None
    assert result.id == UUID(int=10)
    assert record.used_at == now

    retry = FakeSession([record])
    assert (
        await TelegramWebLoginService(cast(AsyncSession, retry)).consume(
            "x" * 32, now=now
        )
        is None
    )


async def test_expired_login_token_is_rejected() -> None:
    now = datetime(2026, 8, 15, 12, tzinfo=UTC)
    record = WebLoginToken(
        id=UUID(int=11),
        user_id=UUID(int=10),
        token_hash="a" * 64,
        expires_at=now - timedelta(seconds=1),
        used_at=None,
    )

    result = await TelegramWebLoginService(
        cast(AsyncSession, FakeSession([record]))
    ).consume("x" * 32, now=now)

    assert result is None
    assert record.used_at is None
