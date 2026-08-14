"""PostgreSQL notification outbox repository."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.application.notifications import ClaimedNotification
from k_loto.domain.enums import NotificationStatus
from k_loto.infrastructure.database.models import NotificationOutbox, User


class SqlNotificationRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def claim_next(self, now: datetime) -> ClaimedNotification | None:
        expired_lock = now - timedelta(minutes=5)
        async with self._session_factory() as session, session.begin():
            row = (
                await session.execute(
                    select(NotificationOutbox, User.telegram_id)
                    .join(User, User.id == NotificationOutbox.user_id)
                    .where(
                        or_(
                            and_(
                                NotificationOutbox.status.in_(
                                    [
                                        NotificationStatus.PENDING,
                                        NotificationStatus.FAILED,
                                    ]
                                ),
                                NotificationOutbox.available_at <= now,
                            ),
                            and_(
                                NotificationOutbox.status
                                == NotificationStatus.PROCESSING,
                                NotificationOutbox.locked_at < expired_lock,
                            ),
                        )
                    )
                    .order_by(
                        NotificationOutbox.available_at,
                        NotificationOutbox.created_at,
                    )
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
            ).one_or_none()
            if row is None:
                return None
            event, telegram_id = row
            event.status = NotificationStatus.PROCESSING
            event.locked_at = now
            event.attempts += 1
            return ClaimedNotification(
                id=event.id,
                event_key=event.event_key,
                chat_id=telegram_id,
                type=event.type,
                payload=event.payload,
                attempts=event.attempts,
            )

    async def mark_sent(self, notification_id: UUID, now: datetime) -> None:
        async with self._session_factory() as session, session.begin():
            event = await session.scalar(
                select(NotificationOutbox)
                .where(NotificationOutbox.id == notification_id)
                .with_for_update()
            )
            if event is None or event.status == NotificationStatus.SENT:
                return
            event.status = NotificationStatus.SENT
            event.sent_at = now
            event.locked_at = None
            event.last_error = None

    async def mark_failed(
        self, notification_id: UUID, now: datetime, error_code: str
    ) -> None:
        async with self._session_factory() as session, session.begin():
            event = await session.scalar(
                select(NotificationOutbox)
                .where(NotificationOutbox.id == notification_id)
                .with_for_update()
            )
            if event is None or event.status == NotificationStatus.SENT:
                return
            event.status = NotificationStatus.FAILED
            event.available_at = now + timedelta(seconds=min(2**event.attempts, 3600))
            event.locked_at = None
            event.last_error = error_code[:128]
