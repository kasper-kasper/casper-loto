"""Telegram identity, formatting and durable dispatch tests."""

from datetime import UTC, datetime
from types import SimpleNamespace
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
from k_loto.infrastructure.database.models import Balance, LedgerTransaction
from k_loto.infrastructure.telegram_bot import miniapp_markup, miniapp_menu_button
from k_loto.infrastructure.telegram_messages import (
    BotNotificationFormatter,
    format_delivery_test,
    format_inactivity_reminder,
    format_jackpot_win,
    format_purchase_message,
    format_result_message,
    format_system_alert,
)


class TransactionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeIdentitySession:
    def __init__(self, user_id: UUID, balance: int) -> None:
        self._values = iter(
            [
                user_id,
                balance,
                Balance(user_id=user_id, amount=balance, version=1),
                None,
                None,
            ]
        )
        self.executed = 0
        self.added: list[Any] = []

    def begin(self) -> TransactionContext:
        return TransactionContext()

    async def scalar(self, _statement: object) -> Any:
        return next(self._values)

    async def execute(self, _statement: object) -> Any:
        if getattr(_statement, "is_select", False):
            return SimpleNamespace(first=lambda: None)
        self.executed += 1

    def add(self, value: Any) -> None:
        self.added.append(value)


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

    async def send(self, notification: ClaimedNotification, text: str) -> None:
        if self.fail:
            raise RuntimeError("sensitive transport details")
        assert notification.chat_id is not None
        self.messages.append((notification.chat_id, text))


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
    assert profile.balance == 100_000_000_500
    assert session.executed == 2
    grants = [item for item in session.added if isinstance(item, LedgerTransaction)]
    assert len(grants) == 1
    assert grants[0].amount == 100_000_000_000


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
    assert button.text == "🎟 Играть в Casper Loto"
    assert button.web_app is not None
    assert button.web_app.url == "https://example.test/miniapp"

    menu_button = miniapp_menu_button("https://example.test/miniapp")
    assert menu_button.text == "🎟 Играть в Casper Loto"
    assert menu_button.web_app.url == "https://example.test/miniapp"


def test_purchase_message_contains_all_tickets_and_balance() -> None:
    message = format_purchase_message(purchase_payload())

    assert "№0010" in message
    assert "№0011" in message
    assert "1 · 2 · 3 · 4 · 5" in message
    assert "списано 200 CAS" in message
    assert "Осталось на счету: 1 800 CAS" in message


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

    assert "16.08.2026 · 20:00 МСК" in message
    assert "совпало 2" in message
    assert "выигрыш 25 CAS" in message
    assert "Твой выигрыш: 25 CAS" in message


def test_inactivity_reminder_names_the_next_draw_without_purchase_noise() -> None:
    message = format_inactivity_reminder(
        {
            "lottery_name": "ПСС-Лото",
            "draw_number": 44,
            "scheduled_at": "2026-09-02T09:00:00+00:00",
        }
    )

    assert "ПСС-Лото №0044" in message
    assert "02.09.2026 · 12:00 МСК" in message
    assert "Вы давно не выбирали числа" in message


def test_jackpot_message_uses_the_owner_copy_and_actual_player_win() -> None:
    payload = {
        "lottery_name": "FLASH",
        "draw_number": 44,
        "scheduled_at": "2026-09-15T12:00:00+00:00",
        "win_amount": 1_234_567,
    }
    message = format_jackpot_win(payload)

    assert message.startswith(
        "Ну ниче се! Ты сорвал кучу бабла, правда виртуальных, а быть может это знак?"
    )
    assert "Тираж: FLASH №0044" in message
    assert "Дата: 15.09.2026 · 15:00 МСК" in message
    assert "Выигрыш: 1 234 567 CAS" in message
    assert (
        BotNotificationFormatter().format(
            ClaimedNotification(
                id=UUID(int=19),
                event_key="jackpot-win:test",
                chat_id=123,
                type=NotificationType.JACKPOT_WIN,
                payload=payload,
                attempts=1,
            )
        )
        == message
    )


def test_delivery_diagnostic_is_explicit_and_does_not_expose_payload() -> None:
    assert "проверочное сообщение" in format_delivery_test().lower()


def test_owner_alert_is_redacted_and_points_to_admin_panel() -> None:
    message = format_system_alert(
        {"kind": "scheduler_error", "count": 1, "error_code": "DatabaseError"}
    )

    assert "ошибка планировщика" in message
    assert "Admin Panel" in message
    assert "DatabaseError" in message


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


@pytest.mark.parametrize("changed", [False, True])
async def test_initialized_identity_reads_without_balance_lock_or_grant(changed):
    from k_loto.infrastructure.database.models import User

    user = User(id=UUID(int=12), username="owner", display_name="Owner")

    class Ready(FakeIdentitySession):
        async def execute(self, statement):
            assert "FOR UPDATE" not in str(statement)
            self.executed += 1
            return SimpleNamespace(first=lambda: (user, 4321))

        async def scalar(self, statement):
            raise AssertionError("Initialized read must not initialize or lock funds")

    session = Ready(user.id, 4321)
    result = await TelegramIdentityService(cast(AsyncSession, session)).bind(
        telegram_id=123,
        username="new" if changed else "owner",
        display_name="New" if changed else "Owner",
    )
    assert result.balance == 4321
    assert session.executed == 1 and not session.added
    assert user.username == ("new" if changed else "owner")
    assert user.display_name == result.display_name
