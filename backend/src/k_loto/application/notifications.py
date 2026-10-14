"""Transport-independent durable notification dispatch orchestration."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from k_loto.domain.enums import NotificationType


class DeliveryRejected(Exception):
    """Transport confirmed that Telegram did not accept the message."""


class DeliveryThrottled(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = max(1, retry_after)


@dataclass(frozen=True, slots=True)
class ClaimedNotification:
    id: UUID
    event_key: str
    chat_id: int | None
    type: NotificationType
    payload: dict[str, Any]
    attempts: int
    cancellation_reason: str | None = None


class NotificationRepository(Protocol):
    async def claim_next(self, now: datetime) -> ClaimedNotification | None: ...

    async def mark_sent(
        self, notification_id: UUID, now: datetime, *, attempt: int
    ) -> None: ...

    async def mark_failed(
        self,
        notification_id: UUID,
        now: datetime,
        error_code: str,
        *,
        attempt: int,
        retry_after: int | None = None,
    ) -> None: ...

    async def mark_uncertain(
        self, notification_id: UUID, now: datetime, *, attempt: int
    ) -> None: ...

    async def mark_cancelled(
        self, notification_id: UUID, now: datetime, error_code: str, *, attempt: int
    ) -> None: ...


class NotificationSender(Protocol):
    async def send(self, notification: ClaimedNotification, text: str) -> None: ...


class NotificationFormatter(Protocol):
    def format(self, notification: ClaimedNotification) -> str: ...


class NotificationDispatcher:
    """Claim and send one event; sent events are never claimed again."""

    def __init__(
        self,
        repository: NotificationRepository,
        sender: NotificationSender,
        formatter: NotificationFormatter,
    ) -> None:
        self._repository = repository
        self._sender = sender
        self._formatter = formatter

    async def process_one(self, now: datetime) -> bool:
        notification = await self._repository.claim_next(now)
        if notification is None:
            return False
        if notification.chat_id is None or notification.cancellation_reason:
            await self._repository.mark_cancelled(
                notification.id,
                now,
                notification.cancellation_reason or "telegram_identity_missing",
                attempt=notification.attempts,
            )
            return True
        try:
            text = self._formatter.format(notification)
        except Exception:
            await self._repository.mark_cancelled(
                notification.id,
                now,
                "notification_format_invalid",
                attempt=notification.attempts,
            )
            return True
        try:
            await self._sender.send(notification, text)
        except DeliveryThrottled as error:
            await self._repository.mark_failed(
                notification.id,
                datetime.now(UTC),
                "telegram_rate_limited",
                attempt=notification.attempts,
                retry_after=error.retry_after,
            )
        except DeliveryRejected:
            await self._repository.mark_cancelled(
                notification.id,
                now,
                "telegram_delivery_rejected",
                attempt=notification.attempts,
            )
        except Exception:
            await self._repository.mark_uncertain(
                notification.id, datetime.now(UTC), attempt=notification.attempts
            )
        else:
            await self._repository.mark_sent(
                notification.id, datetime.now(UTC), attempt=notification.attempts
            )
        return True
