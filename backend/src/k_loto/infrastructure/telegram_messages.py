"""Friendly player notification formatting kept safely below Telegram limits."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from k_loto.application.notifications import ClaimedNotification
from k_loto.domain.enums import NotificationType

MOSCOW = ZoneInfo("Europe/Moscow")
TICKET_PREVIEW_LIMIT = 12


def format_cas(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def _display_numbers(numbers: list[int], lottery_code: str) -> str:
    if lottery_code == "weekly" and len(numbers) == 7:
        main = [value for value in numbers if value <= 35]
        special = [value - 35 for value in numbers if value > 35]
        return f"{' · '.join(map(str, main))}  +  {' · '.join(map(str, special))}"
    return " · ".join(str(value) for value in numbers)


def _display_matches(matches: int, lottery_code: str, *, grand_format: bool) -> str:
    if lottery_code == "weekly" and grand_format:
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
        f"🎲 {payload['lottery_name']} · тираж №{int(payload['draw_number']):04d}\n"
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
        f"{payload['lottery_name']} · тираж №{int(payload['draw_number']):04d}\n"
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
        f"Ближайший тираж — {payload['lottery_name']} "
        f"№{int(payload['draw_number']):04d}.\n"
        f"🕒 {scheduled:%d.%m.%Y · %H:%M} МСК\n\n"
        "Вы давно не выбирали числа. Откройте K-Loto, если хотите участвовать."
    )


def format_delivery_test() -> str:
    return (
        "✅ Уведомления K-Loto работают\n\n"
        "Это проверочное сообщение, которое вы запросили в профиле Mini App. "
        "Результаты ваших тиражей будут приходить сюда."
    )


def format_system_alert(payload: dict[str, Any]) -> str:
    return (
        "🚨 K-Loto: требуется внимание владельца\n\n"
        f"Событие: {payload.get('kind', 'unknown')}\n"
        f"Количество: {int(payload.get('count', 1))}\n"
        "Подробности доступны в Admin Panel. Секретные данные в сообщение не включены."
    )


class BotNotificationFormatter:
    def format(self, notification: ClaimedNotification) -> str:
        if notification.type == NotificationType.TICKET_PURCHASED:
            return format_purchase_message(notification.payload)
        if notification.type == NotificationType.DRAW_RESULT:
            return format_result_message(notification.payload)
        if notification.type == NotificationType.INACTIVITY_REMINDER:
            return format_inactivity_reminder(notification.payload)
        if notification.type == NotificationType.DELIVERY_TEST:
            return format_delivery_test()
        if notification.type == NotificationType.SYSTEM_ALERT:
            return format_system_alert(notification.payload)
        raise ValueError(f"Unsupported notification type: {notification.type}")
