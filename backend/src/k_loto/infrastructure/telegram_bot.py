"""aiogram player bot adapter and notification worker."""

import asyncio
from contextlib import suppress
from datetime import UTC, datetime

import structlog
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from k_loto.application.identity import TelegramIdentityService
from k_loto.application.notifications import NotificationDispatcher
from k_loto.core.config import get_settings
from k_loto.infrastructure.database.session import session_factory
from k_loto.infrastructure.notification_repository import SqlNotificationRepository
from k_loto.infrastructure.telegram_messages import (
    BotNotificationFormatter,
    format_cas,
)

logger = structlog.get_logger(__name__)
router = Router(name="player")


def miniapp_markup(url: str | None) -> InlineKeyboardMarkup | None:
    if not url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть K-Loto",
                    web_app=WebAppInfo(url=url),
                )
            ]
        ]
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    """Idempotently bind a Telegram identity and show the current CAS balance."""
    telegram_user = message.from_user
    if telegram_user is None:
        return
    display_name = " ".join(
        value for value in (telegram_user.first_name, telegram_user.last_name) if value
    )
    async with session_factory() as session:
        profile = await TelegramIdentityService(session).bind(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            display_name=display_name,
        )
    miniapp_url = get_settings().miniapp_url
    await message.answer(
        "K-Loto\n\n"
        "Профиль привязан. Покупка билетов будет доступна через Mini App.\n"
        f"Баланс: {format_cas(profile.balance)} CAS",
        reply_markup=miniapp_markup(str(miniapp_url) if miniapp_url else None),
    )


class AiogramSender:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send(self, chat_id: int, text: str) -> None:
        await self._bot.send_message(chat_id=chat_id, text=text)


async def run_outbox(bot: Bot, interval_seconds: int) -> None:
    dispatcher = NotificationDispatcher(
        SqlNotificationRepository(session_factory),
        AiogramSender(bot),
        BotNotificationFormatter(),
    )
    while True:
        try:
            processed = await dispatcher.process_one(datetime.now(UTC))
        except Exception:
            logger.exception("notification_outbox_iteration_failed")
            processed = False
        if not processed:
            await asyncio.sleep(interval_seconds)


async def run_bot() -> None:
    settings = get_settings()
    if settings.lottery_bot_token is None:
        raise RuntimeError("LOTTERY_BOT_TOKEN is missing.")
    token = settings.lottery_bot_token.get_secret_value().strip()
    if not token:
        raise RuntimeError("LOTTERY_BOT_TOKEN is empty.")

    bot = Bot(token=token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    outbox_task = asyncio.create_task(
        run_outbox(bot, settings.bot_outbox_interval_seconds),
        name="telegram-outbox",
    )
    try:
        await dispatcher.start_polling(bot)
    finally:
        outbox_task.cancel()
        with suppress(asyncio.CancelledError):
            await outbox_task
        await bot.session.close()
        logger.info("telegram_bot_stopped")


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
