"""aiogram gameplay adapter and durable notification worker."""

import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from uuid import uuid4

import structlog
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from k_loto.application.bot_gameplay import TelegramGameplayQueryService
from k_loto.application.identity import TelegramIdentityService
from k_loto.application.notifications import NotificationDispatcher
from k_loto.application.weekly import WeeklyTicketPurchaseService
from k_loto.core.config import get_settings
from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InvalidTicket,
    NoAvailableDraw,
)
from k_loto.infrastructure.database.session import session_factory
from k_loto.infrastructure.notification_repository import SqlNotificationRepository
from k_loto.infrastructure.telegram_game_ui import (
    add_weekly_to_cart,
    back_markup,
    format_draws,
    format_home,
    format_picker,
    format_statistics,
    format_tickets,
    lottery_menu_markup,
    main_menu_markup,
    random_weekly_numbers,
    rules_text,
    telegram_checkout_idempotency_key,
    ticket_tabs_markup,
    toggle_weekly_number,
    weekly_picker_markup,
)
from k_loto.infrastructure.telegram_messages import BotNotificationFormatter, format_cas

logger = structlog.get_logger(__name__)
router = Router(name="player")


class GameplayState(StatesGroup):
    weekly_picker = State()


def miniapp_markup(url: str | None) -> InlineKeyboardMarkup | None:
    """Preserved compatibility entry point for the frozen Mini App."""
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


async def _bind_player(message: Message) -> int | None:
    telegram_user = message.from_user
    if telegram_user is None:
        return None
    display_name = " ".join(
        value for value in (telegram_user.first_name, telegram_user.last_name) if value
    )
    async with session_factory() as session:
        await TelegramIdentityService(session).bind(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            display_name=display_name,
        )
    return telegram_user.id


async def _show_home(message: Message, telegram_id: int, *, edit: bool) -> None:
    async with session_factory() as session:
        home = await TelegramGameplayQueryService(session).home(
            telegram_id, now=datetime.now(UTC)
        )
    if edit:
        await message.edit_text(format_home(home), reply_markup=main_menu_markup())
    else:
        await message.answer(format_home(home), reply_markup=main_menu_markup())


async def _callback_message(
    callback: CallbackQuery, *, answer: bool = True
) -> Message | None:
    if answer:
        await callback.answer()
    return callback.message if isinstance(callback.message, Message) else None


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    """Bind a Telegram player and open the gameplay menu."""
    await state.clear()
    telegram_id = await _bind_player(message)
    if telegram_id is not None:
        await _show_home(message, telegram_id, edit=False)


@router.message(Command("menu"))
async def menu_command(message: Message, state: FSMContext) -> None:
    await start(message, state)


@router.callback_query(F.data == "bot:home")
async def home_callback(callback: CallbackQuery, state: FSMContext) -> None:
    message = await _callback_message(callback)
    if message is None or callback.from_user is None:
        return
    await state.clear()
    await _show_home(message, callback.from_user.id, edit=True)


@router.callback_query(F.data == "bot:buy")
async def buy_menu(callback: CallbackQuery, state: FSMContext) -> None:
    message = await _callback_message(callback)
    if message is None:
        return
    await state.clear()
    await message.edit_text(
        "🎟 Выберите лотерею\n\n"
        "Weekly доступна для покупки. Daily отображается, но останется "
        "закрытой до утверждения payout model и cutoff.",
        reply_markup=lottery_menu_markup(),
    )


@router.callback_query(F.data == "game:daily")
async def daily_unavailable(callback: CallbackQuery) -> None:
    await callback.answer(
        "Daily пока недоступна: экономика и cutoff не утверждены.", show_alert=True
    )


async def _registered_weekly_price(telegram_id: int) -> int:
    async with session_factory() as session:
        home = await TelegramGameplayQueryService(session).home(
            telegram_id, now=datetime.now(UTC)
        )
    weekly = next((item for item in home.lotteries if item.code == "weekly"), None)
    if weekly is None or weekly.ticket_price is None or not weekly.purchase_available:
        raise ConfigurationError("Weekly purchase is not currently available.")
    return weekly.ticket_price


async def _render_picker(message: Message, state: FSMContext, telegram_id: int) -> None:
    data = await state.get_data()
    selected = tuple(int(value) for value in data.get("selected", []))
    cart = tuple(
        tuple(int(number) for number in values) for values in data.get("cart", [])
    )
    try:
        price = await _registered_weekly_price(telegram_id)
    except (ConfigurationError, LookupError):
        await state.clear()
        await message.edit_text(
            "Weekly сейчас недоступна для покупки.", reply_markup=back_markup()
        )
        return
    await message.edit_text(
        format_picker(selected=selected, cart=cart, price=price),
        reply_markup=weekly_picker_markup(selected, len(cart)),
    )


@router.callback_query(F.data == "game:weekly")
async def weekly_start(callback: CallbackQuery, state: FSMContext) -> None:
    message = await _callback_message(callback)
    if message is None:
        return
    await state.set_state(GameplayState.weekly_picker)
    await state.set_data({"selected": [], "cart": [], "checkout_key": str(uuid4())})
    await _render_picker(message, state, callback.from_user.id)


@router.callback_query(GameplayState.weekly_picker, F.data.startswith("pick:"))
async def weekly_action(callback: CallbackQuery, state: FSMContext) -> None:
    message = await _callback_message(callback, answer=False)
    if message is None or callback.data is None:
        return
    action = callback.data.removeprefix("pick:")
    data = await state.get_data()
    selected = tuple(int(value) for value in data.get("selected", []))
    cart = tuple(
        tuple(int(number) for number in values) for values in data.get("cart", [])
    )
    try:
        if action.isdigit():
            selected = toggle_weekly_number(selected, int(action))
        elif action == "random":
            selected = random_weekly_numbers()
        elif action == "clear":
            selected = ()
        elif action == "add":
            cart = add_weekly_to_cart(
                cart,
                selected,
                maximum=get_settings().bot_max_tickets_per_purchase,
            )
            selected = ()
        elif action == "checkout":
            await _checkout_weekly(callback, message, state, selected, cart, data)
            return
        else:
            return
    except ValueError as error:
        await callback.answer(str(error), show_alert=True)
        return
    await state.update_data(
        selected=list(selected), cart=[list(numbers) for numbers in cart]
    )
    await callback.answer()
    await _render_picker(message, state, callback.from_user.id)


async def _checkout_weekly(
    callback: CallbackQuery,
    message: Message,
    state: FSMContext,
    selected: tuple[int, ...],
    cart: tuple[tuple[int, ...], ...],
    data: dict[str, object],
) -> None:
    combinations: list[list[int] | tuple[int, ...]] = list(cart)
    if len(selected) == 5:
        combinations.append(selected)
    if not combinations:
        await callback.answer(
            "Выберите 5 чисел или добавьте билет в корзину.", show_alert=True
        )
        return
    maximum = get_settings().bot_max_tickets_per_purchase
    if len(combinations) > maximum:
        await callback.answer(
            f"Не более {maximum} билетов за одну покупку.",
            show_alert=True,
        )
        return
    checkout_key = str(data.get("checkout_key") or uuid4())
    try:
        async with session_factory() as query_session:
            player = await TelegramGameplayQueryService(query_session).player(
                callback.from_user.id
            )
        async with session_factory() as purchase_session:
            result = await WeeklyTicketPurchaseService(purchase_session).purchase(
                user_id=player.id,
                combinations=combinations,
                idempotency_key=telegram_checkout_idempotency_key(
                    callback.from_user.id, checkout_key
                ),
                now=datetime.now(UTC),
            )
    except InsufficientBalance:
        await callback.answer("Недостаточно CAS на балансе.", show_alert=True)
        return
    except (ConfigurationError, InvalidTicket, NoAvailableDraw):
        await callback.answer(
            "Покупка сейчас недоступна. Обновите меню и попробуйте ещё раз.",
            show_alert=True,
        )
        return
    await state.clear()
    status = "уже была обработана" if result.already_processed else "проведена"
    await callback.answer()
    await message.edit_text(
        "✅ Покупка "
        f"{status}.\n\nБилетов: {len(result.ticket_ids)}\n"
        f"Списано: {format_cas(result.total_cost)} CAS\n"
        f"Баланс: {format_cas(result.balance_after)} CAS\n\n"
        "Подробное подтверждение будет доставлено отдельным защищённым уведомлением.",
        reply_markup=main_menu_markup(),
    )


@router.callback_query(F.data == "bot:balance")
async def balance_callback(callback: CallbackQuery) -> None:
    message = await _callback_message(callback)
    if message is None:
        return
    async with session_factory() as session:
        player = await TelegramGameplayQueryService(session).player(
            callback.from_user.id
        )
    await message.edit_text(
        f"💰 Баланс\n\n{format_cas(player.balance)} CAS",
        reply_markup=back_markup(),
    )


@router.callback_query(F.data.startswith("bot:tickets:"))
async def tickets_callback(callback: CallbackQuery) -> None:
    message = await _callback_message(callback)
    if message is None or callback.data is None:
        return
    active = callback.data.endswith(":active")
    async with session_factory() as session:
        tickets = await TelegramGameplayQueryService(session).tickets(
            callback.from_user.id, active=active
        )
    await message.edit_text(
        format_tickets(tickets, active=active),
        reply_markup=ticket_tabs_markup(active),
    )


@router.callback_query(F.data == "bot:results")
async def results_callback(callback: CallbackQuery) -> None:
    message = await _callback_message(callback)
    if message is None:
        return
    async with session_factory() as session:
        draws = await TelegramGameplayQueryService(session).recent_draws()
    await message.edit_text(format_draws(draws), reply_markup=back_markup())


@router.callback_query(F.data == "bot:statistics")
async def statistics_callback(callback: CallbackQuery) -> None:
    message = await _callback_message(callback)
    if message is None:
        return
    async with session_factory() as session:
        statistics = await TelegramGameplayQueryService(session).statistics(
            callback.from_user.id
        )
    await message.edit_text(format_statistics(statistics), reply_markup=back_markup())


@router.callback_query(F.data == "bot:rules")
async def rules_callback(callback: CallbackQuery) -> None:
    message = await _callback_message(callback)
    if message is not None:
        await message.edit_text(rules_text(), reply_markup=back_markup())


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
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Открыть K-Loto"),
            BotCommand(command="menu", description="Главное игровое меню"),
        ]
    )
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
