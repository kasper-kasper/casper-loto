"""Production boundary and fixture tests for local browser development."""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

import pytest
from fastapi import HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from k_loto.api.routes.miniapp import create_local_dev_session
from k_loto.application.dev_mode import DevBootstrapConfig, DevBootstrapService
from k_loto.core.config import Settings
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    LedgerTransaction,
    Lottery,
)
from k_loto.infrastructure.local_dev_auth import (
    InvalidLocalDevSession,
    is_loopback_authority,
    is_loopback_host,
    is_loopback_origin,
    issue_local_dev_session,
    validate_local_dev_session,
)


class TransactionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeSession:
    def __init__(self, values: Iterable[Any]) -> None:
        self.values = iter(values)
        self.added: list[Any] = []

    def begin(self) -> TransactionContext:
        return TransactionContext()

    async def scalar(self, _statement: object) -> Any:
        return next(self.values)

    def add(self, value: Any) -> None:
        self.added.append(value)


def settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        **overrides,
    )


def request(origin: str, client: str = "127.0.0.1") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/miniapp/dev/session",
            "headers": [
                (b"origin", origin.encode()),
                (b"host", b"127.0.0.1:8000"),
            ],
            "client": (client, 50000),
        }
    )


def test_signed_local_session_validates_and_expires() -> None:
    now = datetime(2026, 8, 15, 10, tzinfo=UTC)
    secret = "a" * 32
    token = issue_local_dev_session(secret, now=now, max_age_seconds=300)

    validate_local_dev_session(token, secret, now=now + timedelta(seconds=299))
    with pytest.raises(InvalidLocalDevSession, match="expired"):
        validate_local_dev_session(token, secret, now=now + timedelta(seconds=300))


def test_tampered_local_session_is_rejected() -> None:
    token = issue_local_dev_session("a" * 32)

    with pytest.raises(InvalidLocalDevSession, match="invalid"):
        validate_local_dev_session(token + "changed", "a" * 32)


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "::1"])
def test_loopback_hosts_are_accepted(host: str) -> None:
    assert is_loopback_host(host)


def test_public_hosts_and_origins_are_rejected() -> None:
    assert not is_loopback_host("example.com")
    assert not is_loopback_origin("https://example.com")
    assert is_loopback_origin("http://127.0.0.1:5173")
    assert is_loopback_authority("localhost:5173")
    assert not is_loopback_authority("random.trycloudflare.com")


def test_production_can_never_enable_local_dev_auth() -> None:
    config = settings(
        app_env="production",
        miniapp_dev_auth_enabled=True,
        miniapp_dev_session_secret="a" * 32,
    )

    assert not config.local_dev_auth_available


async def test_dev_session_endpoint_is_hidden_in_production() -> None:
    with pytest.raises(HTTPException) as caught:
        await create_local_dev_session(
            request("http://127.0.0.1:5173"),
            Response(),
            settings(
                app_env="production",
                miniapp_dev_auth_enabled=True,
                miniapp_dev_session_secret="a" * 32,
            ),
        )

    assert caught.value.status_code == 404


async def test_dev_session_cookie_is_httponly_and_loopback_only() -> None:
    response = Response()
    result = await create_local_dev_session(
        request("http://localhost:5173"),
        response,
        settings(
            app_env="development",
            miniapp_dev_auth_enabled=True,
            miniapp_dev_session_secret="a" * 32,
        ),
    )

    assert result.mode == "local-development"
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    with pytest.raises(HTTPException) as caught:
        await create_local_dev_session(
            request("https://public.example"),
            Response(),
            settings(
                miniapp_dev_auth_enabled=True,
                miniapp_dev_session_secret="a" * 32,
            ),
        )
    assert caught.value.status_code == 403


async def test_dev_bootstrap_creates_playable_ledgered_fixture() -> None:
    user_id = UUID(int=50)
    balance = Balance(user_id=user_id, amount=0, version=1)
    fake = FakeSession([None, balance, *([None] * 30)])
    service = DevBootstrapService(
        cast(AsyncSession, fake),
        DevBootstrapConfig(
            initial_user_balance=100_000,
            weekly_ticket_price=100,
            weekly_base_jackpot=10_000,
            weekly_reserve=100_000,
        ),
    )

    await service.ensure(user_id, now=datetime(2026, 8, 15, 10, tzinfo=UTC))

    lotteries = [item for item in fake.added if isinstance(item, Lottery)]
    draws = [item for item in fake.added if isinstance(item, Draw)]
    ledger = [item for item in fake.added if isinstance(item, LedgerTransaction)]
    assert {item.code for item in lotteries} == {"weekly", "pll", "pss", "khan"}
    assert len(draws) == 4
    assert balance.amount == 100_000
    assert len(ledger) == 10
    assert sum(item.amount for item in ledger) == 1_000_000_000_540_000


async def test_dev_refill_is_an_explicit_ledger_credit() -> None:
    user_id = UUID(int=51)
    balance = Balance(user_id=user_id, amount=50, version=1)
    fake = FakeSession([balance])
    service = DevBootstrapService(
        cast(AsyncSession, fake),
        DevBootstrapConfig(
            initial_user_balance=100_000,
            weekly_ticket_price=100,
            weekly_base_jackpot=10_000,
            weekly_reserve=100_000,
        ),
    )

    result = await service.refill_user(user_id, 1_000)

    ledger = [item for item in fake.added if isinstance(item, LedgerTransaction)]
    assert result == 1_050
    assert balance.amount == 1_050
    assert len(ledger) == 1
    assert ledger[0].balance_before == 50
    assert ledger[0].balance_after == 1_050
