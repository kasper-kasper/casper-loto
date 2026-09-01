"""Database-backed detection and owner alerts for stalled operations."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.domain.enums import (
    DrawStatus,
    NotificationStatus,
    NotificationType,
)
from k_loto.infrastructure.database.models import Draw, NotificationOutbox, User


@dataclass(frozen=True, slots=True)
class OperationalHealth:
    stuck_draws: int
    stuck_notifications: int


class OperationalMonitoringService:
    """Inspect durable state and queue redacted alerts for the configured owner."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        owner_telegram_id: int | None,
        stuck_after: timedelta,
    ) -> None:
        self._session_factory = session_factory
        self._owner_telegram_id = owner_telegram_id
        self._stuck_after = stuck_after

    async def run(self, *, now: datetime | None = None) -> OperationalHealth:
        timestamp = now or datetime.now(UTC)
        stale_before = timestamp - self._stuck_after
        async with self._session_factory() as session, session.begin():
            stuck_draws = int(
                await session.scalar(
                    select(func.count(Draw.id)).where(
                        Draw.status.in_([DrawStatus.DRAWING, DrawStatus.SETTLING]),
                        Draw.updated_at < stale_before,
                    )
                )
                or 0
            )
            stuck_notifications = int(
                await session.scalar(
                    select(func.count(NotificationOutbox.id)).where(
                        or_(
                            (NotificationOutbox.status == NotificationStatus.PROCESSING)
                            & (NotificationOutbox.locked_at < stale_before),
                            (NotificationOutbox.status == NotificationStatus.FAILED)
                            & (NotificationOutbox.attempts >= 5),
                        )
                    )
                )
                or 0
            )
            if stuck_draws:
                await self._queue_alert(session, "stuck_draws", stuck_draws, timestamp)
            if stuck_notifications:
                await self._queue_alert(
                    session,
                    "stuck_notifications",
                    stuck_notifications,
                    timestamp,
                )
        return OperationalHealth(stuck_draws, stuck_notifications)

    async def alert_scheduler_error(
        self, error_code: str, *, now: datetime | None = None
    ) -> None:
        timestamp = now or datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            await self._queue_alert(
                session,
                "scheduler_error",
                1,
                timestamp,
                error_code=error_code[:128],
            )

    async def _queue_alert(
        self,
        session: AsyncSession,
        kind: str,
        count: int,
        now: datetime,
        *,
        error_code: str | None = None,
    ) -> None:
        if self._owner_telegram_id is None:
            return
        owner_id = await session.scalar(
            select(User.id).where(User.telegram_id == self._owner_telegram_id)
        )
        if owner_id is None:
            return
        bucket = int(now.timestamp() // 3600)
        event_key = f"system-alert:{kind}:{bucket}"
        exists = await session.scalar(
            select(NotificationOutbox.id).where(
                NotificationOutbox.event_key == event_key
            )
        )
        if exists is not None:
            return
        payload: dict[str, object] = {"kind": kind, "count": count}
        if error_code:
            payload["error_code"] = error_code
        session.add(
            NotificationOutbox(
                id=uuid4(),
                event_key=event_key,
                user_id=owner_id,
                type=NotificationType.SYSTEM_ALERT,
                status=NotificationStatus.PENDING,
                payload=payload,
                attempts=0,
                available_at=now,
            )
        )
