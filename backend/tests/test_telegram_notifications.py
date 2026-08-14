"""Telegram identity, formatting and durable dispatch tests."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.identity import TelegramIdentityService
from k_loto.application.notifications import (
    ClaimedNotification,
    NotificationDispatcher,
)
from k_loto.domain.enums import NotificationType
from k_loto.infrastructure.telegram_bot import miniapp_markup
from k_loto.infrastructure.telegram_messages import (
    BotNotificationFormatter,
    format_purchase_message,
    format_result_message,
)


class TransactionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeIdentitySession:
    def __init__(self, user_id: UUID, balance: int) -> None:
        self._values = iter([user_id, balance])
        self.executed = 0

    def begin(self) -> TransactionContext:
        return TransactionContext()

    async def scalar(self, _statement: object) -> Any:
        return next(self._values)

    async def execute(self, _statement: object) -> None:
        self.executed += 1


class FakeRepository:
    def __init__(self, event: ClaimedNotification | None) -> None:
        self.event = event
        self.sent: list[UUID] = []
        self.failed: list[tuple[UUID, str]] = []

    async def claim_next(self, _now: datetime) -> ClaimedNotification | None:
        event, self.event = self.event, None
        return event

    async def mark_sent(self, notification_id: UUID, _now: datetime) -> None:
        self.sent.append(notification_id)

    async def mark_failed(
        self, notification_id: UUID, _now: datetime, error_code: str
    ) -> None:
        self.failed.append((notification_id, error_code))


class FakeSender:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.messages: list[tuple[int, str]] = []

    async def send(self, chat_id: int, text: str) -> None:
        if self.fail:
            raise RuntimeError("sensitive transport details")
        self.messages.append((chat_id, text))


def purchase_payload() -> dict[str, Any]:
    return {
        "lottery_name": "Weekly 5/20",
        "draw_number": 7,
        "tickets": [
            {"public_number": 10, "numbers": [1, 2, 3, 4, 5]},
            {"public_number": 11, "numbers": [1, 2, 3, 4, 5]},
        ],
        "total_cost": 200,
        "balance_after": 1_800,
    }


async def test_telegram_identity_binding_is_idempotent_and_creates_balance() -> None:
    user_id = UUID(int=11)
    session = FakeIdentitySession(user_id, 500)

    profile = await TelegramIdentityService(cast(AsyncSession, session)).bind(
        telegram_id=6073224376,
        username="owner",
        display_name=" K Loto ",
    )

    assert profile.id == user_id
    assert profile.display_name == "K Loto"
    assert profile.balance == 500
    assert session.executed == 1


async def test_telegram_identity_rejects_invalid_id() -> None:
    session = FakeIdentitySession(UUID(int=1), 0)
    with pytest.raises(ValueError):
        await TelegramIdentityService(cast(AsyncSession, session)).bind(
            telegram_id=0, username=None, display_name="Player"
        )


def test_miniapp_launch_button_is_only_added_when_url_is_configured() -> None:
    assert miniapp_markup(None) is None

    markup = miniapp_markup("https://example.test/miniapp")

    assert markup is not None
    button = markup.inline_keyboard[0][0]
    assert button.text == "Открыть K-Loto"
    assert button.web_app is not None
    assert button.web_app.url == "https://example.test/miniapp"


def test_purchase_message_contains_all_tickets_and_balance() -> None:
    message = format_purchase_message(purchase_payload())

    assert "Билет 0010" in message
    assert "Билет 0011" in message
    assert "1 • 2 • 3 • 4 • 5" in message
    assert "Списано: 200 CAS" in message
    assert "Баланс: 1 800 CAS" in message


def test_draw_result_message_contains_each_ticket_result() -> None:
    message = format_result_message(
        {
            "lottery_name": "Weekly 5/20",
            "draw_number": 7,
            "scheduled_at": "2026-08-16T17:00:00+00:00",
            "winning_numbers": [1, 2, 3, 4, 5],
            "tickets": [
                {
                    "public_number": 10,
                    "numbers": [1, 2, 8, 9, 10],
                    "matches": 2,
                    "prize": 25,
                }
            ],
            "total_prize": 25,
            "balance_after": 1_825,
        }
    )

    assert "Дата: 2026-08-16 20:00 MSK" in message
    assert "Совпадений: 2" in message
    assert "Выигрыш: 25 CAS" in message
    assert "Общий выигрыш: 25 CAS" in message


async def test_dispatcher_sends_claimed_event_only_once() -> None:
    event = ClaimedNotification(
        id=UUID(int=20),
        event_key="purchase:one",
        chat_id=123,
        type=NotificationType.TICKET_PURCHASED,
        payload=purchase_payload(),
        attempts=1,
    )
    repository = FakeRepository(event)
    sender = FakeSender()
    dispatcher = NotificationDispatcher(repository, sender, BotNotificationFormatter())
    now = datetime(2026, 8, 14, tzinfo=UTC)

    assert await dispatcher.process_one(now)
    assert not await dispatcher.process_one(now)
    assert len(sender.messages) == 1
    assert repository.sent == [event.id]
    assert repository.failed == []


async def test_dispatch_failure_records_only_redacted_error_code() -> None:
    event = ClaimedNotification(
        id=UUID(int=21),
        event_key="purchase:failure",
        chat_id=123,
        type=NotificationType.TICKET_PURCHASED,
        payload=purchase_payload(),
        attempts=1,
    )
    repository = FakeRepository(event)
    dispatcher = NotificationDispatcher(
        repository, FakeSender(fail=True), BotNotificationFormatter()
    )

    assert await dispatcher.process_one(datetime(2026, 8, 14, tzinfo=UTC))
    assert repository.sent == []
    assert repository.failed == [(event.id, "telegram_send_failed")]
