"""Friendly player notification formatting kept safely below Telegram limits."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from k_loto.application.notifications import ClaimedNotification
from k_loto.domain.enums import NotificationType
from k_loto.infrastructure.brand_names import display_brand_name

MOSCOW = ZoneInfo("Europe/Moscow")
TICKET_PREVIEW_LIMIT = 12


def format_cas(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def _display_numbers(numbers: list[int], lottery_code: str) -> str:
    if lottery_code == "newyear2027":
        from k_loto.domain.newyear import SYMBOLS

        return " · ".join(SYMBOLS[value - 1] for value in numbers)
    if lottery_code == "pss" and len(numbers) == 6:
        main = [value for value in numbers if value <= 36]
        special = [value - 36 for value in numbers if value > 36]
        return f"{' · '.join(map(str, main))}  +  Casper Ball {special[0]}"
    if lottery_code == "weekly" and len(numbers) == 7:
        main = [value for value in numbers if value <= 35]
        special = [value - 35 for value in numbers if value > 35]
        return f"{' · '.join(map(str, main))}  +  {' · '.join(map(str, special))}"
    if lottery_code == "pulse" and len(numbers) == 3:
        main = [value for value in numbers if value <= 10]
        special = [value - 10 for value in numbers if value > 10]
        return f"{' · '.join(map(str, main))}  +  P{' · P'.join(map(str, special))}"
    return " · ".join(str(value) for value in numbers)


def _display_matches(matches: int, lottery_code: str, *, grand_format: bool) -> str:
    if lottery_code == "weekly" and grand_format:
        return f"{matches // 10}+{matches % 10}"
    if lottery_code == "pulse":
        return f"{matches // 10}+{matches % 10}"
    return str(matches)


def _ticket_lines(
    tickets: list[dict[str, Any]], *, include_result: bool, lottery_code: str
) -> str:
    ordered = tickets
    if include_result:
        ordered = sorted(
            tickets,
            key=lambda ticket: (
                -int(ticket.get("prize", 0)),
                -int(ticket.get("matches", 0)),
            ),
        )
    visible = ordered[:TICKET_PREVIEW_LIMIT]
    sections: list[str] = []
    for ticket in visible:
        number = int(ticket["public_number"])
        numbers = _display_numbers(list(ticket["numbers"]), lottery_code)
        line = f"🎫 №{number:04d}: {numbers}"
        if include_result:
            matches = _display_matches(
                int(ticket["matches"]),
                lottery_code,
                grand_format=len(ticket["numbers"]) == 7,
            )
            line += (
                f"\n   совпало {matches} · "
                f"выигрыш {format_cas(int(ticket['prize']))} CAS"
            )
        sections.append(line)
    hidden = len(ordered) - len(visible)
    if hidden:
        sections.append(f"…и ещё {hidden} билетов — все они сохранены в «Моих билетах»")
    return "\n".join(sections)


def _scheduled_line(payload: dict[str, Any]) -> str:
    raw = payload.get("scheduled_at")
    if not raw:
        return ""
    scheduled = datetime.fromisoformat(str(raw)).astimezone(MOSCOW)
    return f"🕒 {scheduled:%d.%m.%Y · %H:%M} МСК\n"


def format_purchase_message(payload: dict[str, Any]) -> str:
    tickets = list(payload["tickets"])
    prize_fund = int(payload.get("prize_fund", 0))
    ticket_lines = _ticket_lines(
        tickets,
        include_result=False,
        lottery_code=str(payload.get("lottery_code", "")),
    )
    return (
        "🎟 Готово — билеты уже в игре!\n\n"
        f"🎲 {display_brand_name(str(payload['lottery_name']))} · "
        f"тираж №{int(payload['draw_number']):04d}\n"
        f"{_scheduled_line(payload)}"
        f"🎁 Призовой фонд: {format_cas(prize_fund)} CAS\n\n"
        f"{ticket_lines}\n\n"
        f"Куплено: {len(tickets)} бил. · "
        f"списано {format_cas(int(payload['total_cost']))} CAS\n"
        f"💰 Осталось на счету: {format_cas(int(payload['balance_after']))} CAS\n\n"
        "Теперь можно расслабиться — о результате напишу сам 🍀"
    )


def format_result_message(payload: dict[str, Any]) -> str:
    scheduled = datetime.fromisoformat(str(payload["scheduled_at"])).astimezone(MOSCOW)
    lottery_code = str(payload.get("lottery_code", ""))
    winning = _display_numbers(list(payload["winning_numbers"]), lottery_code)
    tickets = list(payload["tickets"])
    total_prize = int(payload["total_prize"])
    prize_fund = int(payload.get("prize_fund", 0))

    if total_prize > 0:
        heading = "🔥 Есть выигрыш! Вот это поворот"
        ending = f"💸 Твой выигрыш: {format_cas(total_prize)} CAS"
    elif tickets:
        heading = "🎲 Тираж сыгран — сверяем числа"
        ending = "Сегодня без выигрыша, но билеты проверены до последней цифры."
    else:
        heading = "🎉 Новый тираж уже в истории"
        ending = "В этот раз ты смотрел со стороны. Следующий шанс уже ждёт в меню."

    ticket_section = (
        _ticket_lines(tickets, include_result=True, lottery_code=lottery_code)
        if tickets
        else "У тебя не было билетов на этот тираж."
    )
    balance = payload.get("balance_after")
    balance_line = (
        f"\n💰 Баланс: {format_cas(int(balance))} CAS" if balance is not None else ""
    )
    return (
        f"{heading}\n\n"
        f"{display_brand_name(str(payload['lottery_name']))} · "
        f"тираж №{int(payload['draw_number']):04d}\n"
        f"🕒 {scheduled:%d.%m.%Y · %H:%M} МСК\n"
        f"✨ Выпало: {winning}\n\n"
        f"{ticket_section}\n\n"
        f"{ending}{balance_line}\n"
        f"🎁 Призовой фонд: {format_cas(prize_fund)} CAS"
    )


def format_inactivity_reminder(payload: dict[str, Any]) -> str:
    scheduled = datetime.fromisoformat(str(payload["scheduled_at"])).astimezone(MOSCOW)
    return (
        "🎟 Можно снова испытать удачу\n\n"
        f"Ближайший тираж — {display_brand_name(str(payload['lottery_name']))} "
        f"№{int(payload['draw_number']):04d}.\n"
        f"🕒 {scheduled:%d.%m.%Y · %H:%M} МСК\n\n"
        "Вы давно не выбирали числа. Откройте Casper Loto, если хотите участвовать."
    )


def format_jackpot_win(payload: dict[str, Any]) -> str:
    scheduled = datetime.fromisoformat(str(payload["scheduled_at"])).astimezone(MOSCOW)
    return (
        "Ну ниче се! Ты сорвал кучу бабла, правда виртуальных, "
        "а быть может это знак?\n\n"
        f"Тираж: {display_brand_name(str(payload['lottery_name']))} "
        f"№{int(payload['draw_number']):04d}\n"
        f"Дата: {scheduled:%d.%m.%Y · %H:%M} МСК\n"
        f"Выигрыш: {format_cas(int(payload['win_amount']))} CAS"
    )


def format_delivery_test() -> str:
    return (
        "✅ Уведомления Casper Loto работают\n\n"
        "Это проверочное сообщение, которое вы запросили в профиле Mini App. "
        "Сюда придёт сообщение о вашем джекпоте или напоминание об игре."
    )


def format_owner_economy(payload: dict[str, Any]) -> str:
    def cash(key: str, signed: bool = False) -> str:
        value = int(payload[key])
        return f"{'+' if signed and value > 0 else ''}{format_cas(value)} CAS"

    runway = payload["fund_runway_days"]
    days = int(payload["trend_days"])
    warnings = []
    if int(payload["pending_draws"]):
        warnings.append(
            "⚠️ Не завершено тиражей за отчётный день: "
            f"{int(payload['pending_draws'])}. "
            "Итоги могут дополниться."
        )
    if int(payload["fund_balance"]) == 0:
        warnings.append("🚨 Фонд Каспера пуст. Проверь возможность выплат.")
    elif runway == 0:
        warnings.append("⚠️ Фонда меньше чем на день при текущем темпе расхода.")
    if runway is not None:
        horizon = "больше 10 лет" if runway > 3650 else f"около {runway} дн."
        average = (
            f"Средний расход: {cash('fund_daily_expense')}/день "
            f"за {days} полных дней.\n"
            if "fund_daily_expense" in payload
            else ""
        )
        estimate = (
            f"{average}Запас при таком расходе: {horizon}. Это оценка, не гарантия."
        )
    elif days:
        estimate = (
            f"За {days} полных дней фонд не сокращался в сумме. "
            "Для оценки запаса нет устойчивого расхода."
        )
    else:
        estimate = "Для оценки расхода ещё нет полных дней нового этапа."
    partial = " · часть дня после обновления экономики" if payload["partial"] else ""
    supply = int(payload["supply_net"])
    direction = (
        "Валюты стало больше"
        if supply > 0
        else "Валюты стало меньше"
        if supply < 0
        else "Объём валюты не изменился"
    )
    activity = (
        f"👥 Новых игроков: {int(payload['new_players'])}\n"
        f"Покупали билеты: {int(payload['buyers'])} игроков\n\n"
        if "new_players" in payload
        else ""
    )
    types = (
        f"• FAST: {int(payload['fast_tickets'])}\n"
        f"• Мгновенные: {int(payload['instant_tickets'])}\n"
        f"• Тиражные: {int(payload['regular_tickets'])}\n"
        if "fast_tickets" in payload
        else f"Тиражные и FAST: {int(payload['regular_tickets'])}\n"
        f"Мгновенные: {int(payload['instant_tickets'])}\n"
    )
    gifts = (
        f"Подарочных выдано отдельно: {int(payload['gift_tickets'])}\n"
        if "gift_tickets" in payload
        else ""
    )
    refunds = (
        f"Из купленных возвращено билетов: {int(payload['refunded_tickets'])}\n"
        if payload.get("refunded_tickets")
        else ""
    )
    achievements = (
        f"Награды за достижения: {cash('achievement_rewards')}\n"
        if "achievement_rewards" in payload
        else ""
    )
    snapshots = (
        f"У игроков на балансах: {cash('player_balances')}\n"
        f"В джекпотах: {cash('jackpots')}\n"
        if "player_balances" in payload
        else ""
    )
    status = (
        "\n".join(warnings)
        if warnings
        else "Незавершённых тиражей за отчётный день нет. Фонд не пуст."
    )
    return (
        f"Casper Loto · итоги {payload['report_day']} (МСК){partial}\n\n"
        f"{activity}"
        f"🎟 Куплено платных билетов: {int(payload['total_tickets'])}\n"
        f"{types}{refunds}{gifts}\n"
        f"💰 Игроки потратили на билеты: {cash('purchases')}\n"
        f"Выплачено выигрышей: {cash('prizes')}\n"
        f"Возвраты: {cash('refunds')}\n"
        f"{achievements}"
        f"Бонусы и прочие начисления: {cash('other_credit')}\n"
        f"Ручные изменения балансов: {cash('admin_net', True)}\n"
        f"Изменение балансов игроков: {cash('player_net', True)}\n\n"
        f"🔥 Сожжено: {cash('burned')}\n"
        f"Создано новых CAS: {cash('issued')}\n"
        f"{direction}: {cash('supply_net', True)}\n\n"
        f"🏦 Фонд сейчас: {cash('fund_balance')}\n"
        f"Изменение фонда за день: {cash('fund_net', True)}\n"
        f"{snapshots}{estimate}\n\n"
        f"{status}\n"
        "Суммы выше — движения CAS, не прибыль проекта. "
        "Переводы из фонда и джекпотов не считаются созданием валюты.\n"
        "Подробности: админка → Экономика."
    )


def format_system_alert(payload: dict[str, Any]) -> str:
    if payload.get("kind") == "owner_daily_economy":
        return format_owner_economy(payload)
    labels = {
        "stuck_draws": "зависшие тиражи",
        "stuck_notifications": "зависшие уведомления",
        "scheduler_error": "ошибка планировщика",
    }
    kind = str(payload.get("kind", "unknown"))
    label = labels.get(kind, "системная проверка")
    count = int(payload.get("count", 1))
    error_code = str(payload.get("error_code", "")).strip()
    details = f"\nТехнический код: {error_code}" if error_code else ""
    return (
        "🚨 Casper Loto: требуется внимание владельца\n\n"
        f"Что произошло: обнаружены {label}.\n"
        f"Количество: {count}.{details}\n\n"
        "Что проверить: Admin Panel → Журналы → Состояние или Уведомления. "
        "Секретные данные в сообщение не включены."
    )


class BotNotificationFormatter:
    def format(self, notification: ClaimedNotification) -> str:
        if notification.type == NotificationType.ACHIEVEMENT:
            return f"Получено достижение: {str(notification.payload['title'])[:160]}"
        if notification.type == NotificationType.TICKET_PURCHASED:
            return format_purchase_message(notification.payload)
        if notification.type == NotificationType.DRAW_RESULT:
            return format_result_message(notification.payload)
        if notification.type == NotificationType.JACKPOT_WIN:
            return format_jackpot_win(notification.payload)
        if notification.type == NotificationType.INACTIVITY_REMINDER:
            return format_inactivity_reminder(notification.payload)
        if notification.type == NotificationType.DELIVERY_TEST:
            return format_delivery_test()
        if notification.type == NotificationType.SYSTEM_ALERT:
            return format_system_alert(notification.payload)
        raise ValueError(f"Unsupported notification type: {notification.type}")
