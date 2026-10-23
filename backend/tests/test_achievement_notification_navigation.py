"""Scoped PostgreSQL regressions: preferences, bounded navigation and privacy."""

import asyncio
import os
import subprocess
import sys
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from k_loto.api.dependencies import (
    CurrentMiniAppUser,
    get_current_miniapp_user,
    get_db_session,
)
from k_loto.core.config import get_settings
from k_loto.infrastructure.database.models import (
    Balance,
    UserNotification,
    UserNotificationPreference,
)
from k_loto.main import create_app
from test_achievements import entry, launch, quiet, seed, tickets


@pytest_asyncio.fixture
async def notification_db(monkeypatch):
    configured = os.environ.get("NOTIFICATION_TEST_DATABASE_URL") or os.environ.get(
        "ACHIEVEMENT_TEST_DATABASE_URL"
    )
    if not configured:
        pytest.skip("Explicit isolated local notification test database required")
    url = make_url(configured)
    assert url.host in {"127.0.0.1", "localhost"}
    assert url.database == "k_loto_achievement_test"
    name = "k_loto_achievement_notifications_" + uuid4().hex
    admin = create_async_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with admin.connect() as connection:
        await connection.execute(
            text(f'CREATE DATABASE "{name}" TEMPLATE "{url.database}"')
        )
    engine = create_async_engine(url.set(database=name), poolclass=NullPool)
    try:
        env = {
            **os.environ,
            "DATABASE_URL": url.set(database=name).render_as_string(
                hide_password=False
            ),
        }
        await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env=env,
            check=True,
            capture_output=True,
        )
        monkeypatch.setenv("APP_ENV", "test")
        get_settings.cache_clear()
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()
        async with admin.connect() as connection:
            await connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        await admin.dispose()
        get_settings.cache_clear()


def client_for(factory, user_id):
    app = create_app()

    async def identity():
        return CurrentMiniAppUser(user_id, 123)

    async def session():
        async with factory() as current:
            yield current

    app.dependency_overrides[get_current_miniapp_user] = identity
    app.dependency_overrides[get_db_session] = session
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_saved_preference_preserves_telegram_and_suppresses_silent_backlog(
    notification_db,
):
    factory = notification_db
    uid, lid, did = await seed(factory)
    other, _, _ = await seed(factory)
    await launch(factory, [entry(target=1), entry(code="second", target=2)])
    await tickets(factory, uid, lid, did, 1)
    await quiet(factory)
    async with client_for(factory, uid) as client:
        profile = (await client.get("/api/v1/miniapp/account")).json()
        assert profile["notification_preferences"]["in_app_enabled"] is True
        assert (
            len((await client.get("/api/v1/miniapp/achievements/unseen")).json()) == 1
        )
        base = {
            "telegram_enabled": False,
            "draw_results_enabled": True,
            "inactivity_reminders_enabled": True,
        }
        off = await client.put(
            "/api/v1/miniapp/notification-preferences",
            json={**base, "in_app_enabled": False},
        )
        assert off.status_code == 200 and off.json()["in_app_enabled"] is False
        assert (await client.get("/api/v1/miniapp/achievements/unseen")).json() == []
        # Existing clients editing Telegram preferences cannot turn popups back on.
        legacy = await client.put(
            "/api/v1/miniapp/notification-preferences",
            json={**base, "telegram_enabled": True},
        )
        assert (
            legacy.json()["telegram_enabled"] is True
            and legacy.json()["in_app_enabled"] is False
        )
        profile = (await client.get("/api/v1/miniapp/account")).json()
        assert profile["notification_preferences"]["in_app_enabled"] is False
        on = await client.put(
            "/api/v1/miniapp/notification-preferences",
            json={**base, "in_app_enabled": True},
        )
        assert on.json()["in_app_enabled"] is True
        assert (await client.get("/api/v1/miniapp/achievements/unseen")).json() == []
        await tickets(factory, uid, lid, did, 1, start=2)
        await quiet(factory)
        notices = (await client.get("/api/v1/miniapp/achievements/unseen")).json()
        assert [item["code"] for item in notices] == ["second"]
        inbox = (await client.get("/api/v1/miniapp/notifications")).json()
        assert len([item for item in inbox if item["type"] == "ACHIEVEMENT"]) == 2
    async with factory() as session:
        preference = await session.get(UserNotificationPreference, uid)
        assert preference.in_app_enabled_at is not None
        assert (
            await session.scalar(
                select(func.count())
                .select_from(UserNotification)
                .where(UserNotification.read_at.is_(None))
            )
            == 2
        )
        assert (await session.get(Balance, uid)).amount == 1_000_000
    async with client_for(factory, other) as client:
        assert (await client.get("/api/v1/miniapp/achievements/unseen")).json() == []
        assert (await client.get("/api/v1/miniapp/account")).json()[
            "notification_preferences"
        ]["in_app_enabled"] is True


async def test_focus_page_category_ownership_and_secret_redaction(
    notification_db,
):
    factory = notification_db
    uid, lid, did = await seed(factory)
    other, _, _ = await seed(factory)
    entries = [
        entry(code=f"rare-{i:02d}", target=1, sort_order=i).model_copy(
            update={"rarity": "rare"}
        )
        for i in range(15)
    ]
    entries.append(entry(code="secret-locked", secret=True, target=999))
    await launch(factory, entries)
    await tickets(factory, uid, lid, did, 1)
    await quiet(factory)
    async with client_for(factory, uid) as client:
        response = await client.get(
            "/api/v1/miniapp/achievements",
            params={
                "category": "common",
                "focus": "rare-14",
                "status": "locked",
                "limit": 3,
            },
        )
        assert response.status_code == 200
        page = response.json()
        assert page["focused_category"] == "rare"
        assert page["focused_item"]["code"] == "rare-14"
        assert page["focused_item"]["status"] == "earned"
        assert len(page["items"]) == 3 and all(
            item["code"] != "rare-14" for item in page["items"]
        )
        assert page["next_offset"] == 3
        hidden = (
            await client.get(
                "/api/v1/miniapp/achievements", params={"focus": "secret-locked"}
            )
        ).json()["focused_item"]
        assert hidden == {
            "code": "secret-locked",
            "rarity": "common",
            "secret": True,
            "status": "locked",
        }
    async with client_for(factory, other) as client:
        target = (
            await client.get(
                "/api/v1/miniapp/achievements", params={"focus": "rare-14"}
            )
        ).json()["focused_item"]
        assert target["status"] == "locked" and target["earned_at"] is None
