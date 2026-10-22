"""PostgreSQL outbox with durable claims and conservative send recovery."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.application.economy import control_state
from k_loto.application.notifications import ClaimedNotification
from k_loto.domain.enums import NotificationStatus, NotificationType
from k_loto.domain.schedules import MOSCOW
from k_loto.infrastructure.database.models import (
    NotificationOutbox,
    User,
    UserNotificationPreference,
)


class SqlNotificationRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        owner_telegram_id: int | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._owner_telegram_id = owner_telegram_id

    async def claim_next(self, now: datetime) -> ClaimedNotification | None:
        async with self._session_factory() as session, session.begin():
            # A lost acknowledgement is not evidence of failed delivery.
            # Never automatically resend an interrupted claim.
            await session.execute(
                update(NotificationOutbox)
                .where(
                    NotificationOutbox.status == NotificationStatus.PROCESSING,
                    or_(
                        NotificationOutbox.locked_at.is_(None),
                        NotificationOutbox.locked_at < now - timedelta(minutes=5),
                    ),
                )
                .values(
                    status=NotificationStatus.UNCERTAIN,
                    locked_at=None,
                    last_error="telegram_delivery_interrupted",
                )
            )
            row = (
                await session.execute(
                    select(NotificationOutbox, User, UserNotificationPreference)
                    .join(User, User.id == NotificationOutbox.user_id)
                    .outerjoin(
                        UserNotificationPreference,
                        UserNotificationPreference.user_id == User.id,
                    )
                    .where(
                        NotificationOutbox.status.in_(
                            [NotificationStatus.PENDING, NotificationStatus.FAILED]
                        ),
                        NotificationOutbox.available_at <= now,
                    )
                    .order_by(
                        NotificationOutbox.available_at, NotificationOutbox.created_at
                    )
                    .limit(1)
                    .with_for_update(skip_locked=True, of=NotificationOutbox)
                )
            ).one_or_none()
            if row is None:
                return None
            event, user, preference = row
            cancellation_reason = None
            if not user.is_active:
                cancellation_reason = "player_inactive"
            elif (
                event.type == NotificationType.SYSTEM_ALERT
                and event.payload.get("kind") == "owner_daily_economy"
            ):
                control = await control_state(session)
                yesterday = (
                    now.astimezone(MOSCOW).date() - timedelta(days=1)
                ).isoformat()
                if user.telegram_id != self._owner_telegram_id:
                    cancellation_reason = "owner_report_recipient_changed"
                elif (
                    event.payload.get("economy_epoch") != control.epoch
                    or event.payload.get("report_day") != yesterday
                ):
                    cancellation_reason = "owner_report_expired"
            elif event.type != NotificationType.SYSTEM_ALERT:
                if event.type in (
                    NotificationType.TICKET_PURCHASED,
                    NotificationType.DRAW_RESULT,
                ):
                    cancellation_reason = "notification_type_retired"
                elif preference is None or not preference.telegram_enabled:
                    cancellation_reason = "telegram_consent_withdrawn"
                elif event.type == NotificationType.ACHIEVEMENT:
                    from k_loto.core.config import get_settings
                    from k_loto.infrastructure.database.achievement_models import (
                        AchievementPlayer,
                    )

                    achievement_player = await session.get(AchievementPlayer, user.id)
                    if (
                        not get_settings().achievements_notifications_enabled
                        or not achievement_player
                        or not achievement_player.telegram_enabled
                    ):
                        cancellation_reason = "achievement_consent_withdrawn"
                elif (
                    event.type == NotificationType.INACTIVITY_REMINDER
                    and not preference.inactivity_reminders_enabled
                ):
                    cancellation_reason = "reminder_consent_withdrawn"
            event.status = NotificationStatus.PROCESSING
            event.locked_at = now
            event.attempts += 1
            return ClaimedNotification(
                id=event.id,
                event_key=event.event_key,
                chat_id=user.telegram_id,
                type=event.type,
                payload=event.payload,
                attempts=event.attempts,
                cancellation_reason=cancellation_reason,
            )

    async def _finish(
        self,
        notification_id: UUID,
        *,
        attempt: int,
        status: NotificationStatus,
        now: datetime,
        error_code: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            event = await session.scalar(
                select(NotificationOutbox)
                .where(NotificationOutbox.id == notification_id)
                .with_for_update()
            )
            if event is None or event.attempts != attempt:
                return
            # Late success can resolve this interrupted claim.
            # It can never resolve a newer attempt.
            allowed = {NotificationStatus.PROCESSING}
            if status == NotificationStatus.SENT:
                allowed.add(NotificationStatus.UNCERTAIN)
            if event.status not in allowed:
                return
            event.status = status
            event.locked_at = None
            event.last_error = error_code
            if status == NotificationStatus.SENT:
                event.sent_at = now
            elif status == NotificationStatus.FAILED:
                event.available_at = now + timedelta(seconds=max(1, retry_after or 1))

    async def mark_sent(
        self, notification_id: UUID, now: datetime, *, attempt: int
    ) -> None:
        await self._finish(
            notification_id, attempt=attempt, status=NotificationStatus.SENT, now=now
        )

    async def mark_failed(
        self,
        notification_id: UUID,
        now: datetime,
        error_code: str,
        *,
        attempt: int,
        retry_after: int | None = None,
    ) -> None:
        await self._finish(
            notification_id,
            attempt=attempt,
            status=NotificationStatus.FAILED,
            now=now,
            error_code=error_code[:128],
            retry_after=retry_after,
        )

    async def mark_uncertain(
        self, notification_id: UUID, now: datetime, *, attempt: int
    ) -> None:
        await self._finish(
            notification_id,
            attempt=attempt,
            status=NotificationStatus.UNCERTAIN,
            now=now,
            error_code="telegram_delivery_uncertain",
        )

    async def mark_cancelled(
        self, notification_id: UUID, now: datetime, error_code: str, *, attempt: int
    ) -> None:
        await self._finish(
            notification_id,
            attempt=attempt,
            status=NotificationStatus.CANCELLED,
            now=now,
            error_code=error_code[:128],
        )
