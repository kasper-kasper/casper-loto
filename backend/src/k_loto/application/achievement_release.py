"""Owner-invoked production preparation, durable delayed start and emergency pause."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.achievement_catalog import (
    CatalogEntry,
    _import_catalog,
    _start_tracking,
)
from k_loto.application.achievements import worker_lock
from k_loto.core.config import get_settings
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementEvent,
    AchievementRuntime,
)


def require_production() -> None:
    if get_settings().app_env != "production":
        raise ValueError("This explicit command requires APP_ENV=production")


def approved_catalog() -> list[CatalogEntry]:
    from k_loto.application.common_achievements import common_catalog
    from k_loto.application.epic_achievements import epic_catalog
    from k_loto.application.legendary_achievements import legendary_catalog
    from k_loto.application.rare_achievements import rare_catalog
    from k_loto.application.uncommon_achievements import uncommon_catalog

    return [
        *common_catalog(),
        *uncommon_catalog(),
        *rare_catalog(),
        *epic_catalog(),
        *legendary_catalog(),
    ]


async def schedule_production(session: AsyncSession, at: datetime) -> datetime:
    """Called only after release health checks. Import definitions, never players."""
    require_production()
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("An explicit timezone is required")
    now = await session.scalar(select(func.clock_timestamp()))
    assert now is not None
    if at <= now:
        raise ValueError("Launch must be scheduled in the future, never backdated")
    if not await worker_lock(session):
        raise ValueError("Achievement worker is busy; retry later")
    runtime = await session.get(AchievementRuntime, 1, with_for_update=True)
    if runtime is None or runtime.started_at is not None or runtime.enabled:
        raise ValueError("Production launch is once-only; never reset progress")
    if runtime.scheduled_at is not None:
        if (
            runtime.scheduled_at == at
            and runtime.scheduled_revision == runtime.catalog_revision
        ):
            return runtime.scheduled_at
        raise ValueError("Cancel the existing schedule before replacing it")
    if await session.scalar(select(func.count()).select_from(AchievementAward)):
        raise ValueError("Unstarted production must not contain test awards")
    entries = approved_catalog()
    if len(entries) != 93 or len({entry.code for entry in entries}) != 93:
        raise ValueError("The approved release must contain exactly 93 definitions")
    await _import_catalog(session, entries)
    runtime.scheduled_at, runtime.scheduled_revision = (
        at.astimezone(UTC),
        runtime.catalog_revision,
    )
    return runtime.scheduled_at


async def activate_due(session: AsyncSession) -> datetime | None:
    """Scheduler checks one singleton row; source table barrier runs once at start."""
    runtime = await session.get(AchievementRuntime, 1)
    if (
        runtime is None
        or runtime.started_at is not None
        or runtime.enabled
        or runtime.scheduled_at is None
        or runtime.processing_paused
    ):
        return None
    now = await session.scalar(select(func.clock_timestamp()))
    assert now is not None
    if now < runtime.scheduled_at:
        return None
    if not await worker_lock(session):
        return None
    runtime = await session.scalar(
        select(AchievementRuntime)
        .where(AchievementRuntime.id == 1)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert runtime is not None
    if (
        runtime.started_at is not None
        or runtime.processing_paused
        or runtime.scheduled_at is None
    ):
        return None
    now = await session.scalar(select(func.clock_timestamp()))
    if now is None or now < runtime.scheduled_at:
        return None
    if runtime.catalog_revision != runtime.scheduled_revision:
        raise ValueError("Prepared catalog changed; activation refused")
    await session.execute(text("SET LOCAL statement_timeout='5s'"))
    return await _start_tracking(session)


async def cancel_schedule(session: AsyncSession) -> None:
    require_production()
    if not await worker_lock(session):
        raise ValueError("Achievement worker is busy; retry later")
    runtime = await session.get(AchievementRuntime, 1, with_for_update=True)
    if runtime is None or runtime.started_at is not None:
        raise ValueError("A started system cannot be reset or unscheduled")
    runtime.scheduled_at = runtime.scheduled_revision = None


async def pause_processing(session: AsyncSession, *, paused: bool) -> None:
    """Keep capturing committed gameplay events while reward work is paused."""
    require_production()
    if not await worker_lock(session):
        raise ValueError("Achievement worker is busy; retry later")
    runtime = await session.get(AchievementRuntime, 1, with_for_update=True)
    if runtime is None:
        raise ValueError("Achievement schema is missing")
    runtime.processing_paused = paused


async def queue_health(session: AsyncSession, now: datetime) -> dict[str, Any]:
    """Once-per-minute operations sample, restricted to the pending-event index."""
    runtime = await session.get(AchievementRuntime, 1)
    if runtime is None:
        return {"enabled": False, "ready": 0, "blocked": 0, "lag_seconds": 0}
    ready = (AchievementEvent.available_at <= now) & (AchievementEvent.attempts < 8)
    row = (
        await session.execute(
            select(
                func.count().filter(ready),
                func.count().filter(AchievementEvent.attempts >= 8),
                func.min(AchievementEvent.available_at).filter(ready),
            ).where(AchievementEvent.processed_at.is_(None))
        )
    ).one()
    return {
        "enabled": runtime.enabled,
        "processing_paused": runtime.processing_paused,
        "scheduled_at": runtime.scheduled_at.isoformat()
        if runtime.scheduled_at
        else None,
        "started_at": runtime.started_at.isoformat() if runtime.started_at else None,
        "activation_overdue": bool(
            runtime.scheduled_at
            and runtime.started_at is None
            and not runtime.processing_paused
            and (now - runtime.scheduled_at).total_seconds() > 60
        ),
        "ready": row[0],
        "blocked": row[1],
        "lag_seconds": max(0, int((now - row[2]).total_seconds())) if row[2] else 0,
    }
