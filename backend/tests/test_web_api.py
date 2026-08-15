"""Ordinary browser client security and route tests."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import HTTPException

from k_loto.api.routes.web import CurrentWebPlayer, web_player_with_csrf
from k_loto.api.routes.web import router as web_router
from k_loto.core.config import Settings
from k_loto.infrastructure.web_auth import (
    InvalidWebSession,
    hash_web_password,
    issue_web_session,
    normalize_web_username,
    validate_web_session,
    verify_web_password,
)
from k_loto.main import create_app


def test_web_session_is_signed_expiring_and_contains_csrf() -> None:
    now = datetime(2026, 8, 15, 12, tzinfo=UTC)
    token, issued = issue_web_session(
        UUID(int=1), UUID(int=2), "w" * 48, now=now, max_age_seconds=600
    )

    validated = validate_web_session(token, "w" * 48, now=now)

    assert validated.account_id == UUID(int=1)
    assert validated.user_id == UUID(int=2)
    assert validated.csrf_token == issued.csrf_token
    assert validated.expires_at == now + timedelta(minutes=10)


def test_web_session_rejects_tampering_and_expiry() -> None:
    now = datetime(2026, 8, 15, 12, tzinfo=UTC)
    token, _ = issue_web_session(
        UUID(int=1), UUID(int=2), "w" * 48, now=now, max_age_seconds=1
    )
    with pytest.raises(InvalidWebSession, match="signature"):
        validate_web_session(token + "x", "w" * 48, now=now)
    with pytest.raises(InvalidWebSession, match="expired"):
        validate_web_session(token, "w" * 48, now=now + timedelta(seconds=2))


def test_web_session_can_be_issued_directly_from_telegram_identity() -> None:
    now = datetime(2026, 8, 15, 12, tzinfo=UTC)
    token, issued = issue_web_session(
        None,
        UUID(int=2),
        "w" * 48,
        now=now,
    )

    validated = validate_web_session(token, "w" * 48, now=now)

    assert issued.account_id is None
    assert validated.account_id is None
    assert validated.user_id == UUID(int=2)


def test_web_credentials_are_normalized_and_argon2_hashed() -> None:
    encoded = hash_web_password("a strong player password")

    assert normalize_web_username("  PLAYER.Name ") == "player.name"
    assert verify_web_password("a strong player password", encoded)
    assert not verify_web_password("wrong password", encoded)
    with pytest.raises(ValueError, match="12"):
        hash_web_password("short")


def test_web_auth_requires_a_long_independent_secret() -> None:
    base = {
        "database_url": "postgresql+asyncpg://test:test@localhost/test",
        "web_session_secret": None,
    }

    assert not Settings(**base).web_auth_available
    assert not Settings(**{**base, "web_session_secret": "short"}).web_auth_available
    assert Settings(**{**base, "web_session_secret": "w" * 48}).web_auth_available


async def test_web_mutations_require_matching_csrf() -> None:
    _, issued = issue_web_session(
        UUID(int=1),
        UUID(int=2),
        "w" * 48,
        now=datetime(2026, 8, 15, 12, tzinfo=UTC),
    )
    player = CurrentWebPlayer(UUID(int=2), "Player", issued)

    assert await web_player_with_csrf(player, issued.csrf_token) is player
    with pytest.raises(HTTPException) as rejected:
        await web_player_with_csrf(player, "wrong")
    assert rejected.value.status_code == 403


def test_web_routes_are_registered() -> None:
    paths = create_app().openapi()["paths"]

    assert "/api/v1/web/auth/login" in paths
    assert "/api/v1/web/auth/telegram" in paths
    assert "/api/v1/web/auth/session" in paths
    assert "/api/v1/web/auth/logout" in paths
    assert "/api/v1/web/dashboard" in paths
    assert "/api/v1/web/tickets" in paths
    assert "/api/v1/web/results" in paths
    assert "/api/v1/web/weekly/purchases" in paths
    assert "/api/v1/web/daily/purchases" in paths


def test_web_purchases_use_a_fresh_financial_transaction_session() -> None:
    purchase_routes = [
        route
        for route in web_router.routes
        if getattr(route, "path", "").endswith("/purchases")
    ]

    assert len(purchase_routes) == 2
    for route in purchase_routes:
        session_dependency = next(
            dependency
            for dependency in route.dependant.dependencies
            if dependency.name == "session"
        )
        assert session_dependency.use_cache is False
