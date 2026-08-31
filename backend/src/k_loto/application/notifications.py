"""Transport-independent durable notification dispatch orchestration."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from k_loto.domain.enums import NotificationType


@dataclass(frozen=True, slots=True)
class ClaimedNotification:
    id: UUID
    event_key: str
    chat_id: int | None
    type: NotificationType
    payload: dict[str, Any]
    attempts: int


class NotificationRepository(Protocol):
    async def claim_next(self, now: datetime) -> ClaimedNotification | None: ...

    async def mark_sent(self, notification_id: UUID, now: datetime) -> None: ...

    async def mark_failed(
        self, notification_id: UUID, now: datetime, error_code: str
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
        if notification.chat_id is None:
            await self._repository.mark_failed(
                notification.id, now, "telegram_identity_missing"
            )
            return True
        try:
            text = self._formatter.format(notification)
            await self._sender.send(notification, text)
        except Exception:
            await self._repository.mark_failed(
                notification.id, now, "telegram_send_failed"
            )
            return True
        await self._repository.mark_sent(notification.id, now)
        return True
