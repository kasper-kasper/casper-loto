"""aiogram gameplay adapter and durable notification worker."""

import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

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

from k_loto.application.bot_gameplay import BotLotteryCard, TelegramGameplayQueryService
from k_loto.application.daily import DailyTicketPurchaseService
from k_loto.application.favorites import FavoriteCombinationService
from k_loto.application.identity import TelegramIdentityService
from k_loto.application.notifications import ClaimedNotification, NotificationDispatcher
from k_loto.application.weekly import WeeklyTicketPurchaseService
from k_loto.core.config import get_settings
from k_loto.domain.enums import NotificationType
from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InvalidTicket,
    NoAvailableDraw,
)
from k_loto.domain.lotteries import DAILY_LOTTERY_CODES, PLAYABLE_LOTTERY_CODES
from k_loto.infrastructure.database.session import session_factory
from k_loto.infrastructure.notification_repository import SqlNotificationRepository
from k_loto.infrastructure.telegram_game_ui import (
    add_daily_to_cart,
    add_weekly_to_cart,
    back_markup,
    daily_picker_markup,
    favorite_combinations_markup,
    format_draws,
    format_favorite_combinations,
    format_home,
    format_lottery_menu,
    format_next_draw,
    format_picker,
    format_statistics,
    format_tickets,
    lottery_menu_markup,
    main_menu_markup,
    next_draw_markup,
    purchase_complete_markup,
    random_daily_numbers,
    random_weekly_numbers,
    rules_text,
    telegram_checkout_idempotency_key,
    ticket_tabs_markup,
    toggle_daily_number,
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
                    text="✨ Открыть K-Loto",
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


async def _send_miniapp(message: Message) -> None:
    settings = get_settings()
    if settings.miniapp_url is None:
        await message.answer(
            "Mini App временно недоступен. Играть можно через кнопки бота."
        )
        return
    await message.answer(
        "✨ Открой K-Loto — вход выполнится автоматически через Telegram.",
        reply_markup=miniapp_markup(str(settings.miniapp_url)),
    )


@router.message(Command("web"))
async def web_command(message: Message) -> None:
    await _bind_player(message)
    await _send_miniapp(message)


@router.callback_query(F.data == "bot:web")
async def web_callback(callback: CallbackQuery) -> None:
    message = await _callback_message(callback)
    if message is not None:
        await _send_miniapp(message)


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
    async with session_factory() as session:
        home = await TelegramGameplayQueryService(session).home(
            callback.from_user.id, now=datetime.now(UTC)
        )
    await message.edit_text(
        format_lottery_menu(home),
        reply_markup=lottery_menu_markup(home.lotteries),
    )


@router.callback_query(F.data == "bot:next")
async def next_draw_callback(callback: CallbackQuery, state: FSMContext) -> None:
    message = await _callback_message(callback)
    if message is None:
        return
    await state.clear()
    timestamp = datetime.now(UTC)
    async with session_factory() as session:
        home = await TelegramGameplayQueryService(session).home(
            callback.from_user.id, now=timestamp
        )
    lottery = next(
        (item for item in home.lotteries if item.scheduled_at is not None), None
    )
    if lottery is None:
        await message.edit_text(
            "⏳ Тиражи сейчас готовятся. Загляни сюда чуть позже.",
            reply_markup=back_markup(),
        )
        return
    await message.edit_text(
        format_next_draw(lottery, now=timestamp),
        reply_markup=next_draw_markup(lottery),
    )


async def _registered_lottery(telegram_id: int, selector: str) -> BotLotteryCard:
    async with session_factory() as session:
        home = await TelegramGameplayQueryService(session).home(
            telegram_id, now=datetime.now(UTC)
        )
    lottery = next(
        (
            item
            for item in home.lotteries
            if (item.selection_key or item.code) == selector
        ),
        None,
    )
    if (
        lottery is None
        or lottery.ticket_price is None
        or not lottery.purchase_available
    ):
        raise ConfigurationError(f"{selector} purchase is not currently available.")
    return lottery


async def _favorite_context(
    telegram_id: int, state: FSMContext
) -> tuple[UUID, BotLotteryCard]:
    data = await state.get_data()
    code = str(data.get("lottery_code", "weekly"))
    selector = str(data.get("lottery_selector", code))
    lottery = await _registered_lottery(telegram_id, selector)
    async with session_factory() as session:
        player = await TelegramGameplayQueryService(session).player(telegram_id)
    return player.id, lottery


async def _show_favorites(
    message: Message,
    state: FSMContext,
    telegram_id: int,
    *,
    page: int = 1,
) -> None:
    player_id, lottery = await _favorite_context(telegram_id, state)
    page_size = 6
    async with session_factory() as session:
        rows = await FavoriteCombinationService(session).list_for_lottery(
            user_id=player_id,
            lottery_id=lottery.id,
            limit=page_size + 1,
            offset=(page - 1) * page_size,
        )
    favorites = rows[:page_size]
    has_next = len(rows) > page_size
    if not favorites and page > 1:
        page = 1
        async with session_factory() as session:
            rows = await FavoriteCombinationService(session).list_for_lottery(
                user_id=player_id,
                lottery_id=lottery.id,
                limit=page_size + 1,
            )
        favorites = rows[:page_size]
        has_next = len(rows) > page_size
    await state.update_data(favorite_page=page)
    await message.edit_text(
        format_favorite_combinations(lottery=lottery, favorites=favorites, page=page),
        reply_markup=favorite_combinations_markup(
            favorites, page=page, has_next=has_next
        ),
    )


async def _render_picker(message: Message, state: FSMContext, telegram_id: int) -> None:
    data = await state.get_data()
    selected = tuple(int(value) for value in data.get("selected", []))
    cart = tuple(
        tuple(int(number) for number in values) for values in data.get("cart", [])
    )
    code = str(data.get("lottery_code", "weekly"))
    selector = str(data.get("lottery_selector", code))
    daily = code in DAILY_LOTTERY_CODES
    try:
        lottery = await _registered_lottery(telegram_id, selector)
    except (ConfigurationError, LookupError):
        await state.clear()
        await message.edit_text(
            "⏳ Этот тираж уже закрыл продажи. Выбери следующий — он совсем рядом.",
            reply_markup=back_markup(),
        )
        return
    await message.edit_text(
        format_picker(
            selected=selected,
            cart=cart,
            price=cast(int, lottery.ticket_price),
            lottery_name=lottery.name,
            numbers_to_pick=4 if daily else 5,
            max_number=15 if daily else 20,
            prize_fund=lottery.jackpot,
            scheduled_at=lottery.scheduled_at,
            draw_number=lottery.draw_number,
        ),
        reply_markup=(
            daily_picker_markup(selected, len(cart))
            if daily
            else weekly_picker_markup(selected, len(cart))
        ),
    )


@router.callback_query(F.data.startswith("game:"))
async def lottery_start(callback: CallbackQuery, state: FSMContext) -> None:
    message = await _callback_message(callback)
    if message is None or callback.data is None:
        return
    selector = callback.data.removeprefix("game:")
    try:
        lottery = await _registered_lottery(callback.from_user.id, selector)
    except (ConfigurationError, LookupError):
        await callback.answer(
            "Этот тираж уже недоступен. Обнови список.", show_alert=True
        )
        return
    await state.set_state(GameplayState.weekly_picker)
    await state.set_data(
        {
            "lottery_code": lottery.code,
            "lottery_selector": selector,
            "draw_id": str(lottery.draw_id) if lottery.draw_id else None,
            "selected": [],
            "cart": [],
            "checkout_key": str(uuid4()),
        }
    )
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
    code = str(data.get("lottery_code", "weekly"))
    daily = code in DAILY_LOTTERY_CODES
    try:
        if action.isdigit():
            selected = (
                toggle_daily_number(selected, int(action))
                if daily
                else toggle_weekly_number(selected, int(action))
            )
        elif action == "random":
            selected = random_daily_numbers() if daily else random_weekly_numbers()
        elif action == "clear":
            selected = ()
        elif action == "save":
            numbers_to_pick = 4 if daily else 5
            if len(selected) != numbers_to_pick:
                raise ValueError(
                    f"Сначала выбери все {numbers_to_pick} чисел комбинации."
                )
            player_id, lottery = await _favorite_context(callback.from_user.id, state)
            async with session_factory() as session:
                _, created = await FavoriteCombinationService(session).save(
                    user_id=player_id,
                    lottery_id=lottery.id,
                    numbers=selected,
                )
            await callback.answer(
                "⭐ Комбинация сохранена!"
                if created
                else "Эта комбинация уже в любимых.",
                show_alert=True,
            )
            await _render_picker(message, state, callback.from_user.id)
            return
        elif action == "favorites":
            await callback.answer()
            await _show_favorites(message, state, callback.from_user.id)
            return
        elif action in {"auto5", "auto10", "auto25", "auto50"}:
            count = int(action.removeprefix("auto"))
            maximum = get_settings().bot_max_tickets_per_purchase
            if len(cart) + count > maximum:
                raise ValueError(f"В корзине может быть до {maximum} билетов.")
            generator = random_daily_numbers if daily else random_weekly_numbers
            cart = (*cart, *(generator() for _ in range(count)))
            selected = ()
        elif action == "add":
            add_to_cart = add_daily_to_cart if daily else add_weekly_to_cart
            cart = add_to_cart(
                cart, selected, maximum=get_settings().bot_max_tickets_per_purchase
            )
            selected = ()
        elif action == "checkout":
            await _checkout_lottery(callback, message, state, selected, cart, data)
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


@router.callback_query(GameplayState.weekly_picker, F.data.startswith("fav:"))
async def favorite_action(callback: CallbackQuery, state: FSMContext) -> None:
    message = await _callback_message(callback, answer=False)
    if message is None or callback.data is None:
        return
    parts = callback.data.split(":", 2)
    action = parts[1] if len(parts) > 1 else ""
    try:
        if action == "back":
            await callback.answer()
            await _render_picker(message, state, callback.from_user.id)
            return
        if action == "page":
            page = max(1, int(parts[2]))
            await callback.answer()
            await _show_favorites(message, state, callback.from_user.id, page=page)
            return
        favorite_id = UUID(parts[2])
        player_id, lottery = await _favorite_context(callback.from_user.id, state)
        if action == "use":
            async with session_factory() as session:
                favorite = await FavoriteCombinationService(session).get(
                    favorite_id=favorite_id,
                    user_id=player_id,
                    lottery_id=lottery.id,
                )
            await state.update_data(selected=list(favorite.numbers))
            await callback.answer("⭐ Числа добавлены в билет")
            await _render_picker(message, state, callback.from_user.id)
            return
        if action == "delete":
            async with session_factory() as session:
                deleted = await FavoriteCombinationService(session).delete(
                    favorite_id=favorite_id,
                    user_id=player_id,
                    lottery_id=lottery.id,
                )
            data = await state.get_data()
            page = max(1, int(data.get("favorite_page", 1)))
            await callback.answer(
                "Удалено из любимых" if deleted else "Комбинация уже удалена"
            )
            await _show_favorites(message, state, callback.from_user.id, page=page)
            return
    except (LookupError, ValueError, ConfigurationError):
        await callback.answer(
            "Не получилось открыть комбинацию. Обнови список.", show_alert=True
        )


async def _checkout_lottery(
    callback: CallbackQuery,
    message: Message,
    state: FSMContext,
    selected: tuple[int, ...],
    cart: tuple[tuple[int, ...], ...],
    data: dict[str, object],
) -> None:
    code = str(data.get("lottery_code", "weekly"))
    daily = code in DAILY_LOTTERY_CODES
    numbers_to_pick = 4 if daily else 5
    combinations: list[list[int] | tuple[int, ...]] = list(cart)
    if len(selected) == numbers_to_pick:
        combinations.append(selected)
    if not combinations:
        await callback.answer(
            f"Выбери {numbers_to_pick} чисел или добавь готовые билеты кнопкой «Авто».",
            show_alert=True,
        )
        return
    maximum = get_settings().bot_max_tickets_per_purchase
    if len(combinations) > maximum:
        await callback.answer(
            f"За один раз можно купить до {maximum} билетов.",
            show_alert=True,
        )
        return
    checkout_key = str(data.get("checkout_key") or uuid4())
    raw_draw_id = data.get("draw_id")
    target_draw_id = UUID(str(raw_draw_id)) if raw_draw_id else None
    purchase_scope = target_draw_id.hex[:12] if target_draw_id else code
    try:
        async with session_factory() as query_session:
            player = await TelegramGameplayQueryService(query_session).player(
                callback.from_user.id
            )
        async with session_factory() as purchase_session:
            purchase_service = (
                DailyTicketPurchaseService(
                    purchase_session, code, target_draw_id=target_draw_id
                )
                if daily
                else WeeklyTicketPurchaseService(
                    purchase_session, code, target_draw_id=target_draw_id
                )
            )
            result = await purchase_service.purchase(
                user_id=player.id,
                combinations=combinations,
                idempotency_key=telegram_checkout_idempotency_key(
                    callback.from_user.id,
                    f"{purchase_scope}:{checkout_key}",
                ),
                now=datetime.now(UTC),
            )
    except InsufficientBalance:
        await callback.answer(
            "На счету не хватает CAS для этой корзины.", show_alert=True
        )
        return
    except (ConfigurationError, InvalidTicket, NoAvailableDraw):
        await callback.answer(
            "Не успели в этот тираж. Обнови список и выбери следующий.",
            show_alert=True,
        )
        return
    await state.clear()
    status = (
        "Покупка уже была сохранена"
        if result.already_processed
        else "Билеты уже в игре"
    )
    await callback.answer()
    await message.edit_text(
        f"✅ {status}!\n\n"
        f"🎟 Билетов: {len(result.ticket_ids)}\n"
        f"Списано: {format_cas(result.total_cost)} CAS\n"
        f"💰 Баланс: {format_cas(result.balance_after)} CAS\n\n"
        "Подробности уже летят отдельным сообщением. О результате тоже напишу сам 🍀",
        reply_markup=purchase_complete_markup(),
    )


@router.callback_query(F.data == "bot:balance")
async def balance_callback(callback: CallbackQuery) -> None:
    message = await _callback_message(callback)
    if message is None:
        return
    async with session_factory() as session:
        home = await TelegramGameplayQueryService(session).home(
            callback.from_user.id, now=datetime.now(UTC)
        )
    funds: dict[str, tuple[str, int]] = {}
    for lottery in home.lotteries:
        funds.setdefault(lottery.code, (lottery.name, lottery.jackpot))
    fund_lines = "\n".join(
        f"🎁 {name}: {format_cas(amount)} CAS" for name, amount in funds.values()
    )
    await message.edit_text(
        "💰 Твой игровой счёт\n\n"
        f"{format_cas(home.player.balance)} CAS\n\n"
        f"Сейчас в призовых фондах:\n{fund_lines}\n\n"
        "Можно идти за билетами — или просто полюбоваться цифрами 😎",
        reply_markup=back_markup(),
    )


@router.callback_query(F.data.startswith("bot:tickets:"))
async def tickets_callback(callback: CallbackQuery) -> None:
    message = await _callback_message(callback)
    if message is None or callback.data is None:
        return
    parts = callback.data.split(":")
    active = len(parts) >= 3 and parts[2] == "active"
    try:
        page = max(1, int(parts[3])) if len(parts) >= 4 else 1
    except ValueError:
        page = 1
    page_size = 10
    async with session_factory() as session:
        page_rows = await TelegramGameplayQueryService(session).tickets(
            callback.from_user.id,
            active=active,
            limit=page_size + 1,
            offset=(page - 1) * page_size,
        )
    tickets = page_rows[:page_size]
    has_next = len(page_rows) > page_size
    if not tickets and page > 1:
        page = 1
        async with session_factory() as session:
            page_rows = await TelegramGameplayQueryService(session).tickets(
                callback.from_user.id,
                active=active,
                limit=page_size + 1,
            )
        tickets = page_rows[:page_size]
        has_next = len(page_rows) > page_size
    await message.edit_text(
        format_tickets(tickets, active=active, page=page),
        reply_markup=ticket_tabs_markup(active, page=page, has_next=has_next),
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

    async def send(self, notification: ClaimedNotification, text: str) -> None:
        if notification.chat_id is None:
            raise ValueError("Telegram chat id is missing.")
        markup = None
        if notification.type == NotificationType.DRAW_RESULT:
            lottery_code = str(notification.payload.get("lottery_code", ""))
            if lottery_code in PLAYABLE_LOTTERY_CODES:
                markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🎟 Купить билет",
                                callback_data=f"game:{lottery_code}",
                            )
                        ]
                    ]
                )
        await self._bot.send_message(
            chat_id=notification.chat_id,
            text=text,
            reply_markup=markup,
        )


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
            BotCommand(command="start", description="Зайти в игру 🎲"),
            BotCommand(command="menu", description="Открыть главное меню"),
            BotCommand(command="web", description="Открыть K-Loto Mini App"),
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
