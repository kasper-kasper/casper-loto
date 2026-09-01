"""Minimal Telegram entry point plus durable notification worker."""

import asyncio
from contextlib import suppress
from datetime import UTC, datetime

import structlog
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from k_loto.application.identity import TelegramIdentityService
from k_loto.application.notifications import ClaimedNotification, NotificationDispatcher
from k_loto.core.config import get_settings
from k_loto.infrastructure.database.session import session_factory
from k_loto.infrastructure.notification_repository import SqlNotificationRepository
from k_loto.infrastructure.telegram_messages import BotNotificationFormatter

logger = structlog.get_logger(__name__)
router = Router(name="player")


def miniapp_markup(url: str | None) -> InlineKeyboardMarkup | None:
    if not url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎟 Играть в K-Loto",
                    web_app=WebAppInfo(url=url),
                )
            ]
        ]
    )


def miniapp_menu_button(url: str) -> MenuButtonWebApp:
    return MenuButtonWebApp(
        text="🎟 Играть в K-Loto",
        web_app=WebAppInfo(url=url),
    )


async def _bind_player(message: Message) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        return
    display_name = " ".join(
        value for value in (telegram_user.first_name, telegram_user.last_name) if value
    )
    async with session_factory() as session:
        await TelegramIdentityService(session).bind(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            display_name=display_name,
        )


async def _send_miniapp(message: Message) -> None:
    settings = get_settings()
    if settings.miniapp_url is None:
        await message.answer(
            "Mini App временно недоступен. Попробуйте открыть K-Loto немного позже."
        )
        return
    await message.answer(
        "✨ Открой K-Loto — вход выполнится автоматически через Telegram.",
        reply_markup=miniapp_markup(str(settings.miniapp_url)),
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    await _bind_player(message)
    await _send_miniapp(message)


@router.message(Command("menu"))
@router.message(Command("web"))
async def miniapp_command(message: Message) -> None:
    await _bind_player(message)
    await _send_miniapp(message)


@router.callback_query(F.data == "bot:web")
async def web_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await _send_miniapp(callback.message)


class AiogramSender:
    def __init__(self, bot: Bot, miniapp_url: str | None) -> None:
        self._bot = bot
        self._miniapp_url = miniapp_url

    async def send(self, notification: ClaimedNotification, text: str) -> None:
        if notification.chat_id is None:
            raise ValueError("Telegram chat id is missing.")
        await self._bot.send_message(
            chat_id=notification.chat_id,
            text=text,
            reply_markup=miniapp_markup(self._miniapp_url),
        )


async def run_outbox(bot: Bot, interval_seconds: int, miniapp_url: str | None) -> None:
    dispatcher = NotificationDispatcher(
        SqlNotificationRepository(session_factory),
        AiogramSender(bot, miniapp_url),
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
    await bot.set_my_commands(
        [BotCommand(command="start", description="Открыть K-Loto")]
    )
    miniapp_url = str(settings.miniapp_url) if settings.miniapp_url else None
    if miniapp_url:
        await bot.set_chat_menu_button(menu_button=miniapp_menu_button(miniapp_url))
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    outbox_task = asyncio.create_task(
        run_outbox(bot, settings.bot_outbox_interval_seconds, miniapp_url),
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
