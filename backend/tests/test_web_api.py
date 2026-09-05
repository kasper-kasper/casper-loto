"""Security boundaries and registration surface for the desktop Web client."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

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


def test_web_session_is_signed_and_expires() -> None:
    now = datetime(2026, 9, 5, 12, tzinfo=UTC)
    token, issued = issue_web_session(
        UUID(int=1), UUID(int=2), "w" * 48, now=now, max_age_seconds=60
    )

    assert validate_web_session(token, "w" * 48, now=now) == issued
    with pytest.raises(InvalidWebSession, match="signature"):
        validate_web_session(token + "x", "w" * 48, now=now)
    with pytest.raises(InvalidWebSession, match="expired"):
        validate_web_session(token, "w" * 48, now=now + timedelta(seconds=61))


def test_web_credentials_are_normalized_and_hashed() -> None:
    encoded = hash_web_password("strong-pass")

    assert normalize_web_username("  Player.Name ") == "player.name"
    assert verify_web_password("strong-pass", encoded)
    assert not verify_web_password("wrong-pass", encoded)
    with pytest.raises(ValueError, match="8"):
        hash_web_password("short")


def test_web_auth_requires_an_independent_secret() -> None:
    base = {"database_url": "postgresql+asyncpg://test:test@localhost/test"}
    assert not Settings(_env_file=None, **base).web_auth_available
    assert not Settings(
        _env_file=None, **base, web_session_secret="short"
    ).web_auth_available
    assert Settings(
        _env_file=None, **base, web_session_secret="w" * 48
    ).web_auth_available


def test_web_routes_cover_desktop_gameplay() -> None:
    paths = create_app().openapi()["paths"]
    expected = {
        "/api/v1/web/auth/register",
        "/api/v1/web/auth/login",
        "/api/v1/web/dashboard",
        "/api/v1/web/account",
        "/api/v1/web/tickets",
        "/api/v1/web/live",
        "/api/v1/web/lotteries/{lottery_code}/purchases",
        "/api/v1/web/bingo/inventory",
        "/api/v1/web/bingo/purchases",
    }
    assert expected <= set(paths)
