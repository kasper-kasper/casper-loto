"""Immediate text delivery, definite throttling and no ambiguous retry."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods import SendMessage

from k_loto.application.distribution import deliver_distribution
from k_loto.infrastructure.database.models import DistributionAnnouncement, Draw

NOW = datetime(2026, 10, 9, tzinfo=UTC)


class Session:
    def __init__(self, row, draw):
        self.row, self.draw = row, draw

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    def begin(self):
        return self

    async def execute(self, _statement):
        return None

    async def scalar(self, statement):
        assert "FOR UPDATE" in str(statement)
        return self.row if self.row.state == "queued" else None

    async def get(self, model, *_args, **_kwargs):
        return self.draw if model is Draw else self.row


def setup():
    row = DistributionAnnouncement(
        id=uuid4(), draw_id=uuid4(), text="Text only", state="queued"
    )
    draw = Draw(scheduled_at=NOW + timedelta(hours=1))
    session = Session(row, draw)
    bot = SimpleNamespace(
        send_message=AsyncMock(return_value=SimpleNamespace(message_id=17))
    )
    return row, bot, lambda: session


async def test_send_is_immediate_text_only_and_once():
    row, bot, factory = setup()
    with patch(
        "k_loto.application.distribution.get_settings",
        return_value=SimpleNamespace(publication_channel="@test"),
    ):
        assert await deliver_distribution(factory, bot, now=NOW) == "sent"
        assert await deliver_distribution(factory, bot, now=NOW) == "empty"
    bot.send_message.assert_awaited_once_with(
        "@test", text="Text only", parse_mode=None
    )
    assert row.state == "sent" and row.message_id == 17


async def test_uncertain_response_cannot_duplicate_post():
    row, bot, factory = setup()
    bot.send_message.side_effect = TimeoutError()
    assert await deliver_distribution(factory, bot, now=NOW) == "uncertain"
    assert await deliver_distribution(factory, bot, now=NOW) == "empty"
    assert row.state == "uncertain" and row.error_type == "TimeoutError"
    assert bot.send_message.await_count == 1


async def test_definite_rate_limit_retains_same_outbox_row():
    row, bot, factory = setup()
    original = row.id
    bot.send_message.side_effect = TelegramRetryAfter(
        method=SendMessage(chat_id=1, text="test"), message="retry", retry_after=5
    )
    assert await deliver_distribution(factory, bot, now=NOW) == "throttled"
    assert row.state == "queued" and row.retry_after is not None and row.id == original


async def test_expired_announcement_never_posts():
    row, bot, factory = setup()
    assert (
        await deliver_distribution(factory, bot, now=NOW + timedelta(hours=1))
        == "expired"
    )
    bot.send_message.assert_not_awaited()
    assert row.state == "expired"
