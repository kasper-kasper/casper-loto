"""Read-only channel permission probe; never consumes updates or sends posts."""

import asyncio
from typing import Any

from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError

from k_loto.core.config import Settings
from k_loto.infrastructure.database.models import PublicationEventState
from k_loto.infrastructure.database.session import session_factory


async def channel_status(settings: Settings, *, check: bool = False) -> dict[str, Any]:
    async with session_factory() as session:
        state = await session.get(PublicationEventState, "publication.transport")
        enabled = bool(state and state.value.get("enabled"))
    result: dict[str, Any] = {
        "channel": settings.publication_channel,
        "delivery_enabled": enabled,
        "checked": False,
        "can_post": False,
    }
    if not check or not settings.publication_channel or not settings.lottery_bot_token:
        return result
    bot = Bot(settings.lottery_bot_token.get_secret_value())
    try:
        async with asyncio.timeout(15):
            identity = await bot.get_me()
            chat = await bot.get_chat(settings.publication_channel)
            member = await bot.get_chat_member(chat.id, identity.id)
            result.update(
                checked=True,
                bot_username=identity.username,
                channel_id=chat.id,
                channel_title=chat.title,
                can_post=chat.type == ChatType.CHANNEL
                and bool(getattr(member, "can_post_messages", False)),
            )
    except (TelegramAPIError, TimeoutError, OSError):
        # Telegram exceptions may contain token-bearing request URLs; don't expose them.
        result.update(
            checked=True,
            error="Не удалось проверить канал. Проверьте адрес и права бота.",
        )
    finally:
        await bot.session.close()
    return result
