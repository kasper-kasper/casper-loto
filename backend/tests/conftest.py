"""Shared test environment setup."""

import os
from types import SimpleNamespace

import pytest

# Legacy editorial services are exercised only with explicit test opt-in.
os.environ.setdefault("EDITORIAL_ENABLED", "true")
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/k_loto_test",
)


@pytest.fixture(autouse=True)
def isolated_economy_gate(monkeypatch):
    """Existing unit fakes model accounts, not the separately tested DB pause gate."""
    from k_loto.api import economy_maintenance
    from k_loto.application import auto_play, economy, instant, scheduler, weekly
    from k_loto.infrastructure import scheduler as runtime

    original_require_open = economy.require_open
    original_is_paused = economy.is_paused

    async def require_open(session):
        if isinstance(session, AsyncSession):
            return await original_require_open(session)
        return SimpleNamespace(paused=False, recovery_after=None)

    async def is_paused(session):
        if isinstance(session, AsyncSession):
            return await original_is_paused(session)
        return False

    for module in (weekly, instant, scheduler):
        monkeypatch.setattr(module, "require_open", require_open)
    for module in (auto_play, scheduler, runtime):
        monkeypatch.setattr(module, "is_paused", is_paused)

    async def public_status(_session):
        return False

    # HTTP unit tests do not have a database. Maintenance HTTP tests override this.
    monkeypatch.setattr(economy_maintenance, "is_paused", public_status)
