"""Permission probes must remain read-only and close their HTTP session."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from k_loto.core.config import Settings
from k_loto.infrastructure.publication_channel import channel_status


async def test_probe_reads_only_identity_channel_and_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = SimpleNamespace(
        get_me=AsyncMock(return_value=SimpleNamespace(id=1, username="test_bot")),
        get_chat=AsyncMock(
            return_value=SimpleNamespace(id=-100123, title="Channel", type="channel")
        ),
        get_chat_member=AsyncMock(return_value=SimpleNamespace(can_post_messages=True)),
        session=SimpleNamespace(close=AsyncMock()),
    )
    monkeypatch.setattr(
        "k_loto.infrastructure.publication_channel.Bot", lambda _token: bot
    )
    settings = Settings(
        publication_channel="@casper_loto",
        lottery_bot_token=SecretStr("not-a-real-token"),
    )
    result = await channel_status(settings, check=True)
    assert result["can_post"] is True and result["delivery_enabled"] is False
    bot.get_chat.assert_awaited_once_with("@casper_loto")
    bot.session.close.assert_awaited_once()


async def test_configuration_read_does_not_connect_to_telegram(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(_token: str) -> None:
        pytest.fail("A configuration read must not construct a Telegram client.")

    monkeypatch.setattr("k_loto.infrastructure.publication_channel.Bot", unexpected)
    result = await channel_status(Settings(publication_channel="@casper_loto"))
    assert result["checked"] is False and result["delivery_enabled"] is False
