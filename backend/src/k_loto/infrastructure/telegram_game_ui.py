"""Pure Telegram gameplay presentation and keyboard construction."""

from datetime import datetime
from secrets import SystemRandom
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from k_loto.application.bot_gameplay import (
    BotDraw,
    BotHome,
    BotPlayerStatistics,
    BotTicket,
)
from k_loto.infrastructure.telegram_messages import format_cas

MOSCOW = ZoneInfo("Europe/Moscow")


def main_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎟 Купить билет", callback_data="bot:buy")],
            [
                InlineKeyboardButton(text="💰 Баланс", callback_data="bot:balance"),
                InlineKeyboardButton(
                    text="🎫 Мои билеты", callback_data="bot:tickets:active"
                ),
            ],
            [
                InlineKeyboardButton(text="🏆 Результаты", callback_data="bot:results"),
                InlineKeyboardButton(
                    text="📊 Статистика", callback_data="bot:statistics"
                ),
            ],
            [InlineKeyboardButton(text="ℹ️ Правила", callback_data="bot:rules")],
        ]
    )


def back_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="← Главное меню", callback_data="bot:home")]
        ]
    )


def lottery_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Weekly 5 из 20", callback_data="game:weekly")],
            [
                InlineKeyboardButton(
                    text="Daily 4 из 15 · скоро", callback_data="game:daily"
                )
            ],
            [InlineKeyboardButton(text="← Главное меню", callback_data="bot:home")],
        ]
    )


def ticket_tabs_markup(active: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="● Активные" if active else "Активные",
                    callback_data="bot:tickets:active",
                ),
                InlineKeyboardButton(
                    text="● История" if not active else "История",
                    callback_data="bot:tickets:history",
                ),
            ],
            [InlineKeyboardButton(text="← Главное меню", callback_data="bot:home")],
        ]
    )


def weekly_picker_markup(
    selected: tuple[int, ...], cart_size: int
) -> InlineKeyboardMarkup:
    selected_set = set(selected)
    rows: list[list[InlineKeyboardButton]] = []
    for start in range(1, 21, 5):
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"✓ {number:02d}" if number in selected_set else f"{number:02d}"
                    ),
                    callback_data=f"pick:{number}",
                )
                for number in range(start, start + 5)
            ]
        )
    rows.extend(
        [
            [
                InlineKeyboardButton(text="🎲 Случайные", callback_data="pick:random"),
                InlineKeyboardButton(text="Очистить", callback_data="pick:clear"),
            ],
            [
                InlineKeyboardButton(
                    text="＋ Добавить в корзину", callback_data="pick:add"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"✅ Купить ({cart_size + (1 if len(selected) == 5 else 0)})",
                    callback_data="pick:checkout",
                )
            ],
            [InlineKeyboardButton(text="← Отмена", callback_data="bot:buy")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def toggle_weekly_number(selected: tuple[int, ...], number: int) -> tuple[int, ...]:
    if number < 1 or number > 20:
        raise ValueError("Weekly number must be between 1 and 20.")
    values = set(selected)
    if number in values:
        values.remove(number)
    elif len(values) >= 5:
        raise ValueError("Weekly ticket already contains five numbers.")
    else:
        values.add(number)
    return tuple(sorted(values))


def random_weekly_numbers(rng: SystemRandom | None = None) -> tuple[int, ...]:
    generator = rng or SystemRandom()
    return tuple(sorted(generator.sample(range(1, 21), 5)))


def add_weekly_to_cart(
    cart: tuple[tuple[int, ...], ...], selected: tuple[int, ...], *, maximum: int
) -> tuple[tuple[int, ...], ...]:
    if len(selected) != 5:
        raise ValueError("Select exactly five numbers before adding a ticket.")
    if len(cart) >= maximum:
        raise ValueError(f"One Telegram purchase supports up to {maximum} tickets.")
    return (*cart, tuple(sorted(selected)))


def telegram_checkout_idempotency_key(telegram_id: int, checkout_key: str) -> str:
    if telegram_id <= 0 or not checkout_key or len(checkout_key) > 100:
        raise ValueError("Telegram checkout identity is invalid.")
    return f"telegram:{telegram_id}:{checkout_key}"


def format_home(home: BotHome) -> str:
    lines = [
        "🎰 K-Loto",
        "",
        f"Игрок: {home.player.display_name}",
        f"Баланс: {format_cas(home.player.balance)} CAS",
        f"Активных билетов: {home.active_ticket_count}",
    ]
    for lottery in home.lotteries:
        lines.extend(
            [
                "",
                f"{lottery.name}",
                f"Джекпот: {format_cas(lottery.jackpot)} CAS",
                (
                    f"Тираж: {lottery.draw_number:04d} · "
                    f"{_moscow(lottery.scheduled_at)}"
                    if lottery.draw_number and lottery.scheduled_at
                    else "Ближайший тираж ещё не подготовлен"
                ),
            ]
        )
    return "\n".join(lines)


def format_picker(
    *, selected: tuple[int, ...], cart: tuple[tuple[int, ...], ...], price: int
) -> str:
    selection = " · ".join(map(str, selected)) if selected else "—"
    lines = [
        "🎟 Weekly 5 из 20",
        "",
        f"Выбрано: {selection} ({len(selected)}/5)",
        f"В корзине: {len(cart)} бил.",
        f"Цена одного билета: {format_cas(price)} CAS",
    ]
    if cart:
        lines.extend(["", "Корзина:"])
        lines.extend(
            f"{index}. {' · '.join(map(str, numbers))}"
            for index, numbers in enumerate(cart, 1)
        )
    lines.extend(
        [
            "",
            "Одинаковые комбинации разрешены. Тираж и итоговая цена "
            "определяются сервером.",
        ]
    )
    return "\n".join(lines)


def format_tickets(tickets: tuple[BotTicket, ...], *, active: bool) -> str:
    title = "🎫 Активные билеты" if active else "🗂 История билетов"
    if not tickets:
        return f"{title}\n\nЗдесь пока нет билетов."
    sections = [title]
    for ticket in tickets:
        lines = [
            "",
            f"{ticket.lottery_name} · тираж {ticket.draw_number:04d}",
            f"Билет {ticket.public_number:04d}: {' · '.join(map(str, ticket.numbers))}",
            f"Дата: {_moscow(ticket.scheduled_at)}",
        ]
        if not active:
            lines.extend(
                [
                    "Результат: "
                    f"{' · '.join(map(str, ticket.winning_numbers or ())) or '—'}",
                    f"Совпадений: {ticket.matches or 0}",
                    f"Выигрыш: {format_cas(ticket.prize_amount)} CAS",
                ]
            )
        sections.extend(lines)
    return "\n".join(sections)


def format_draws(draws: tuple[BotDraw, ...]) -> str:
    if not draws:
        return "🏆 Результаты\n\nЗавершённых тиражей пока нет."
    sections = ["🏆 Последние результаты"]
    for draw in draws:
        sections.extend(
            [
                "",
                f"{draw.lottery_name} · тираж {draw.public_number:04d}",
                f"Дата: {_moscow(draw.scheduled_at)}",
                f"Числа: {' · '.join(map(str, draw.winning_numbers))}",
                f"Билетов: {draw.ticket_count} · "
                f"выплачено {format_cas(draw.total_payout)} CAS",
                f"Переходящий jackpot: {format_cas(draw.jackpot_closing or 0)} CAS",
                f"Distribution: {format_cas(draw.distribution_closing or 0)} CAS",
            ]
        )
    return "\n".join(sections)


def format_statistics(stats: BotPlayerStatistics) -> str:
    match_lines = "\n".join(
        f"{matches}/5: {count}" for matches, count in stats.match_counts.items()
    )
    return (
        "📊 Статистика игрока\n\n"
        f"Куплено билетов: {stats.ticket_count}\n"
        f"Потрачено: {format_cas(stats.spent)} CAS\n"
        f"Выиграно: {format_cas(stats.won)} CAS\n"
        f"Итог: {format_cas(stats.net)} CAS\n"
        f"Лучший выигрыш: {format_cas(stats.best_prize)} CAS\n"
        f"Максимум совпадений: {stats.best_matches}/5\n\n"
        f"Результаты билетов:\n{match_lines}"
    )


def rules_text() -> str:
    return (
        "ℹ️ Weekly 5 из 20\n\n"
        "Выберите 5 уникальных чисел от 1 до 20. Одинаковые комбинации "
        "в разных билетах разрешены.\n\n"
        "0/5 и 1/5 — 0 CAS\n"
        "2/5 — 25% цены билета\n"
        "3/5 — 100% цены билета\n"
        "4/5 — доля оставшегося distribution fund\n"
        "5/5 — доля jackpot\n\n"
        "Продажи Weekly закрываются в воскресенье в 19:55 MSK, тираж "
        "проходит в 20:00 MSK. После cutoff покупка относится к следующему "
        "тиражу. Daily пока недоступна до утверждения экономики."
    )


def _moscow(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone(MOSCOW).strftime("%d.%m.%Y %H:%M MSK")
