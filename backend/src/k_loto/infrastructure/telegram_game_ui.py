"""Friendly Telegram gameplay presentation and keyboard construction."""

from datetime import datetime
from secrets import SystemRandom
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from k_loto.application.bot_gameplay import (
    BotDraw,
    BotHome,
    BotLotteryCard,
    BotPlayerStatistics,
    BotTicket,
)
from k_loto.application.favorites import FavoriteNumbers
from k_loto.infrastructure.telegram_messages import format_cas

MOSCOW = ZoneInfo("Europe/Moscow")


def main_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Выбрать тираж", callback_data="bot:buy")],
            [InlineKeyboardButton(text="⏳ Следующий тираж", callback_data="bot:next")],
            [InlineKeyboardButton(text="✨ Открыть Mini App", callback_data="bot:web")],
            [
                InlineKeyboardButton(text="💰 Мой баланс", callback_data="bot:balance"),
                InlineKeyboardButton(
                    text="🎟 Мои билеты", callback_data="bot:tickets:active"
                ),
            ],
            [
                InlineKeyboardButton(text="🏆 Что выпало", callback_data="bot:results"),
                InlineKeyboardButton(
                    text="📈 Моя игра", callback_data="bot:statistics"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💡 Как всё работает", callback_data="bot:rules"
                )
            ],
        ]
    )


def back_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="← Вернуться в меню", callback_data="bot:home")]
        ]
    )


def lottery_menu_markup(lotteries: tuple[BotLotteryCard, ...]) -> InlineKeyboardMarkup:
    """Offer every prepared draw, including all three Daily time slots."""
    rows: list[list[InlineKeyboardButton]] = []
    for lottery in lotteries:
        icon = "🌙" if lottery.code == "weekly" else "⚡"
        time_label = (
            lottery.scheduled_at.astimezone(MOSCOW).strftime("%d.%m · %H:%M")
            if lottery.scheduled_at
            else "скоро"
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{icon} {lottery.name} · {time_label}",
                    callback_data=f"game:{lottery.selection_key or lottery.code}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="← Вернуться в меню", callback_data="bot:home")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ticket_tabs_markup(
    active: bool, *, page: int = 1, has_next: bool = False
) -> InlineKeyboardMarkup:
    navigation: list[InlineKeyboardButton] = []
    section = "active" if active else "history"
    if page > 1:
        navigation.append(
            InlineKeyboardButton(
                text="← Назад", callback_data=f"bot:tickets:{section}:{page - 1}"
            )
        )
    if has_next:
        navigation.append(
            InlineKeyboardButton(
                text="Дальше →", callback_data=f"bot:tickets:{section}:{page + 1}"
            )
        )
    rows = [
        [
            InlineKeyboardButton(
                text="● В игре" if active else "В игре",
                callback_data="bot:tickets:active:1",
            ),
            InlineKeyboardButton(
                text="● Архив" if not active else "Архив",
                callback_data="bot:tickets:history:1",
            ),
        ]
    ]
    if navigation:
        rows.append(navigation)
    rows.append(
        [InlineKeyboardButton(text="← Вернуться в меню", callback_data="bot:home")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def purchase_complete_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎟 Посмотреть все билеты",
                    callback_data="bot:tickets:active:1",
                )
            ],
            [InlineKeyboardButton(text="← Главное меню", callback_data="bot:home")],
        ]
    )


def next_draw_markup(lottery: BotLotteryCard) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if lottery.purchase_available:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🎟 Выбрать числа",
                    callback_data=f"game:{lottery.selection_key or lottery.code}",
                )
            ]
        )
    rows.extend(
        [
            [InlineKeyboardButton(text="🎲 Все тиражи", callback_data="bot:buy")],
            [InlineKeyboardButton(text="← Главное меню", callback_data="bot:home")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def favorite_combinations_markup(
    favorites: tuple[FavoriteNumbers, ...], *, page: int, has_next: bool
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for favorite in favorites:
        numbers = " · ".join(map(str, favorite.numbers))
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"⭐ {numbers}", callback_data=f"fav:use:{favorite.id}"
                ),
                InlineKeyboardButton(
                    text="✕", callback_data=f"fav:delete:{favorite.id}"
                ),
            ]
        )
    navigation: list[InlineKeyboardButton] = []
    if page > 1:
        navigation.append(
            InlineKeyboardButton(text="← Назад", callback_data=f"fav:page:{page - 1}")
        )
    if has_next:
        navigation.append(
            InlineKeyboardButton(text="Дальше →", callback_data=f"fav:page:{page + 1}")
        )
    if navigation:
        rows.append(navigation)
    rows.append([InlineKeyboardButton(text="← К билету", callback_data="fav:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _picker_actions(cart_size: int, ready: bool) -> list[list[InlineKeyboardButton]]:
    return [
        [
            InlineKeyboardButton(
                text="🎲 Случайные числа", callback_data="pick:random"
            ),
            InlineKeyboardButton(text="Сбросить", callback_data="pick:clear"),
        ],
        [
            InlineKeyboardButton(text="⭐ Сохранить", callback_data="pick:save"),
            InlineKeyboardButton(
                text="⭐ Мои комбинации", callback_data="pick:favorites"
            ),
        ],
        [
            InlineKeyboardButton(text="⚡ Авто ×5", callback_data="pick:auto5"),
            InlineKeyboardButton(text="⚡ Авто ×10", callback_data="pick:auto10"),
        ],
        [
            InlineKeyboardButton(text="⚡ Авто ×25", callback_data="pick:auto25"),
            InlineKeyboardButton(text="⚡ Авто ×50", callback_data="pick:auto50"),
        ],
        [InlineKeyboardButton(text="＋ В корзину", callback_data="pick:add")],
        [
            InlineKeyboardButton(
                text=f"✅ Купить {cart_size + (1 if ready else 0)} бил.",
                callback_data="pick:checkout",
            )
        ],
        [InlineKeyboardButton(text="← Выбрать другой тираж", callback_data="bot:buy")],
    ]


def weekly_picker_markup(
    selected: tuple[int, ...], cart_size: int
) -> InlineKeyboardMarkup:
    selected_set = set(selected)
    rows = [
        [
            InlineKeyboardButton(
                text=f"✓ {number:02d}" if number in selected_set else f"{number:02d}",
                callback_data=f"pick:{number}",
            )
            for number in range(start, start + 5)
        ]
        for start in range(1, 21, 5)
    ]
    rows.extend(_picker_actions(cart_size, len(selected) == 5))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def daily_picker_markup(
    selected: tuple[int, ...], cart_size: int
) -> InlineKeyboardMarkup:
    selected_set = set(selected)
    rows = [
        [
            InlineKeyboardButton(
                text=f"✓ {number:02d}" if number in selected_set else f"{number:02d}",
                callback_data=f"pick:{number}",
            )
            for number in range(start, start + 5)
        ]
        for start in range(1, 16, 5)
    ]
    rows.extend(_picker_actions(cart_size, len(selected) == 4))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def toggle_weekly_number(selected: tuple[int, ...], number: int) -> tuple[int, ...]:
    if number < 1 or number > 20:
        raise ValueError("Число должно быть от 1 до 20.")
    values = set(selected)
    if number in values:
        values.remove(number)
    elif len(values) >= 5:
        raise ValueError("В билете уже выбраны пять чисел.")
    else:
        values.add(number)
    return tuple(sorted(values))


def random_weekly_numbers(rng: SystemRandom | None = None) -> tuple[int, ...]:
    return tuple(sorted((rng or SystemRandom()).sample(range(1, 21), 5)))


def toggle_daily_number(selected: tuple[int, ...], number: int) -> tuple[int, ...]:
    if number < 1 or number > 15:
        raise ValueError("Число должно быть от 1 до 15.")
    values = set(selected)
    if number in values:
        values.remove(number)
    elif len(values) >= 4:
        raise ValueError("В билете уже выбраны четыре числа.")
    else:
        values.add(number)
    return tuple(sorted(values))


def random_daily_numbers(rng: SystemRandom | None = None) -> tuple[int, ...]:
    return tuple(sorted((rng or SystemRandom()).sample(range(1, 16), 4)))


def add_weekly_to_cart(
    cart: tuple[tuple[int, ...], ...], selected: tuple[int, ...], *, maximum: int
) -> tuple[tuple[int, ...], ...]:
    if len(selected) != 5:
        raise ValueError("Сначала выбери ровно пять чисел.")
    if len(cart) >= maximum:
        raise ValueError(f"В одну корзину помещается до {maximum} билетов.")
    return (*cart, tuple(sorted(selected)))


def add_daily_to_cart(
    cart: tuple[tuple[int, ...], ...], selected: tuple[int, ...], *, maximum: int
) -> tuple[tuple[int, ...], ...]:
    if len(selected) != 4:
        raise ValueError("Сначала выбери ровно четыре числа.")
    if len(cart) >= maximum:
        raise ValueError(f"В одну корзину помещается до {maximum} билетов.")
    return (*cart, tuple(sorted(selected)))


def telegram_checkout_idempotency_key(telegram_id: int, checkout_key: str) -> str:
    if telegram_id <= 0 or not checkout_key or len(checkout_key) > 100:
        raise ValueError("Не удалось безопасно определить эту покупку.")
    return f"telegram:{telegram_id}:{checkout_key}"


def _lottery_lines(lotteries: tuple[BotLotteryCard, ...]) -> list[str]:
    lines: list[str] = []
    for lottery in lotteries:
        draw = (
            f"тираж №{lottery.draw_number:04d}" if lottery.draw_number else "готовится"
        )
        icon = "🌙" if lottery.code == "weekly" else "⚡"
        lines.extend(
            [
                f"\n{icon} {lottery.name} · {draw}",
                f"🕒 {_moscow(lottery.scheduled_at)}",
                f"🎁 Призовой фонд: {format_cas(lottery.jackpot)} CAS",
            ]
        )
    return lines


def format_home(home: BotHome) -> str:
    lines = [
        f"🎲 Привет, {home.player.display_name}!",
        "Твои числа, твой выбор, твой момент.",
        "",
        f"💰 Баланс: {format_cas(home.player.balance)} CAS",
        f"🎟 Билетов в игре: {home.active_ticket_count}",
        "",
        "Вот четыре тиража, в которые можно зайти:",
    ]
    lines.extend(_lottery_lines(home.lotteries))
    lines.extend(["", "Выбирай тираж — дальше всё займёт пару нажатий 👇"])
    return "\n".join(lines)


def format_lottery_menu(home: BotHome) -> str:
    lines = [
        "🎯 В какой тираж играем?",
        "Можно взять ближайший или выбрать удобное время.",
    ]
    lines.extend(_lottery_lines(home.lotteries))
    lines.extend(["", f"💰 На счету: {format_cas(home.player.balance)} CAS"])
    return "\n".join(lines)


def format_next_draw(lottery: BotLotteryCard, *, now: datetime) -> str:
    seconds = max(
        0,
        int((lottery.scheduled_at - now).total_seconds())
        if lottery.scheduled_at
        else 0,
    )
    days, remainder = divmod(seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes = remainder // 60
    countdown_parts = []
    if days:
        countdown_parts.append(f"{days} дн.")
    if hours:
        countdown_parts.append(f"{hours} ч.")
    countdown_parts.append(f"{minutes} мин.")
    countdown = " ".join(countdown_parts)
    return (
        "⏳ Ближайший шанс уже на подходе\n\n"
        f"🎲 {lottery.name} · тираж №{lottery.draw_number or 0:04d}\n"
        f"🕒 {_moscow(lottery.scheduled_at)}\n"
        f"⏱ До старта: {countdown}\n\n"
        f"🎁 Призовой фонд: {format_cas(lottery.jackpot)} CAS\n"
        f"🎟 Один билет: {format_cas(lottery.ticket_price or 0)} CAS\n"
        f"🔢 Формат: {lottery.numbers_to_pick} из {lottery.max_number}\n\n"
        "Можно выбрать числа самому, взять любимую комбинацию или довериться удаче."
    )


def format_favorite_combinations(
    *,
    lottery: BotLotteryCard,
    favorites: tuple[FavoriteNumbers, ...],
    page: int,
) -> str:
    lines = [
        f"⭐ Любимые комбинации · {lottery.name}",
        f"🎁 Призовой фонд: {format_cas(lottery.jackpot)} CAS",
        f"Страница {page}",
        "",
    ]
    if favorites:
        lines.extend(
            [
                "Нажми на комбинацию — и она сразу появится в билете.",
                "Крестик справа удаляет её из любимых.",
            ]
        )
    else:
        lines.extend(
            [
                "Здесь пока пусто.",
                "Вернись к билету, выбери числа и нажми «⭐ Сохранить».",
            ]
        )
    return "\n".join(lines)


def format_picker(
    *,
    selected: tuple[int, ...],
    cart: tuple[tuple[int, ...], ...],
    price: int,
    lottery_name: str = "ЛСД-лото",
    numbers_to_pick: int = 5,
    max_number: int = 20,
    prize_fund: int = 0,
    scheduled_at: datetime | None = None,
    draw_number: int | None = None,
) -> str:
    selection = " · ".join(map(str, selected)) if selected else "пока пусто"
    title = f"🎯 {lottery_name}"
    if draw_number:
        title += f" · №{draw_number:04d}"
    lines = [
        title,
        f"🕒 {_moscow(scheduled_at)}",
        f"🎁 Призовой фонд: {format_cas(prize_fund)} CAS",
        f"🎟 Билет: {format_cas(price)} CAS",
        "",
        f"Твои числа ({len(selected)}/{numbers_to_pick}): {selection}",
        f"Выбирай {numbers_to_pick} из {max_number} "
        "или доверься кнопке «Случайные числа».",
        "",
        f"🛒 Корзина: {len(cart)} бил. · {format_cas(len(cart) * price)} CAS",
    ]
    if cart:
        lines.append("")
        preview = cart[:10]
        lines.extend(
            f"{index}. {' · '.join(map(str, numbers))}"
            for index, numbers in enumerate(preview, 1)
        )
        if len(cart) > len(preview):
            lines.append(f"…и ещё {len(cart) - len(preview)} билетов")
    lines.extend(
        [
            "",
            "Хочешь много билетов сразу? Нажми «Авто» — бот соберёт разные комбинации.",
            "Когда всё готово, жми «Купить». Без лишних подтверждений.",
        ]
    )
    return "\n".join(lines)


def format_tickets(
    tickets: tuple[BotTicket, ...], *, active: bool, page: int = 1
) -> str:
    title = "🎟 Билеты в игре" if active else "🗂 Архив билетов"
    title += f" · страница {page}"
    if not tickets:
        ending = (
            "Самое время выбрать первый тираж 🎲"
            if active
            else "История появится после первого розыгрыша."
        )
        return f"{title}\n\nПока здесь пусто. {ending}"
    sections = [title]
    for ticket in tickets:
        ticket_numbers = " · ".join(map(str, ticket.numbers))
        sections.extend(
            [
                "",
                f"{ticket.lottery_name} · тираж №{ticket.draw_number:04d}",
                f"🎫 Билет №{ticket.public_number:04d}: {ticket_numbers}",
                f"🕒 {_moscow(ticket.scheduled_at)}",
            ]
        )
        if not active:
            winning_numbers = " · ".join(map(str, ticket.winning_numbers or ())) or "—"
            sections.extend(
                [
                    f"Выпало: {winning_numbers}",
                    f"Совпало: {ticket.matches or 0} · "
                    f"выигрыш {format_cas(ticket.prize_amount)} CAS",
                ]
            )
    return "\n".join(sections)


def format_draws(draws: tuple[BotDraw, ...]) -> str:
    if not draws:
        return (
            "🏆 Что выпало\n\n"
            "Тиражи ещё разминаются. Скоро здесь появятся первые числа."
        )
    sections = ["🏆 Свежие результаты"]
    for draw in draws:
        sections.extend(
            [
                "",
                f"🎲 {draw.lottery_name} · №{draw.public_number:04d}",
                f"🕒 {_moscow(draw.scheduled_at)}",
                f"Выпало: {' · '.join(map(str, draw.winning_numbers))}",
                f"В игре было {draw.ticket_count} бил. · "
                f"выплачено {format_cas(draw.total_payout)} CAS",
                f"🎁 Призовой фонд: {format_cas(draw.jackpot_closing or 0)} CAS",
            ]
        )
    return "\n".join(sections)


def format_statistics(stats: BotPlayerStatistics) -> str:
    match_lines = "\n".join(
        f"Совпало {matches}: {count} бил."
        for matches, count in stats.match_counts.items()
    )
    mood = (
        "Ты в плюсе — красиво! 🔥"
        if stats.net > 0
        else "Каждый билет добавляет истории новый шанс."
    )
    return (
        "📈 Твоя игра в цифрах\n\n"
        f"🎟 Куплено: {stats.ticket_count} бил.\n"
        f"Потрачено: {format_cas(stats.spent)} CAS\n"
        f"Выиграно: {format_cas(stats.won)} CAS\n"
        f"Итог: {format_cas(stats.net)} CAS\n"
        f"🏅 Лучший выигрыш: {format_cas(stats.best_prize)} CAS\n"
        f"🎯 Лучшее совпадение: {stats.best_matches}\n\n"
        f"{mood}\n\nРазбор билетов:\n{match_lines}"
    )


def rules_text() -> str:
    return (
        "💡 Всё очень просто\n\n"
        "⚡ ПЛЛ, ПСС и ХАН — это одна ежедневная лотерея с общим призовым фондом. "
        "Она играет каждый день в 02:22, 12:00 и 18:00 по Москве. "
        "Выбираешь 4 числа из 15. За 2 совпадения возвращается половина цены билета, "
        "за 3 — тройная цена, за 4 — доля главного фонда.\n\n"
        "🌙 ЛСД-лото играет по воскресеньям в 20:00 по Москве. "
        "Здесь выбираешь 5 чисел из 20. За 2 совпадения — четверть цены билета, "
        "за 3 — полная цена, за 4 и 5 — доля призовых фондов.\n\n"
        "🎲 Можно выбрать числа самому или создать до 50 случайных билетов "
        "одним нажатием. Продажи ежедневных билетов закрываются за 2 минуты, "
        "недельных — за 5 минут до старта.\n\n"
        "🏆 Тираж состоится даже без купленных билетов, "
        "а результат всё равно появится в боте."
    )


def _moscow(value: datetime | None) -> str:
    if value is None:
        return "время уточняется"
    return value.astimezone(MOSCOW).strftime("%d.%m.%Y · %H:%M МСК")
