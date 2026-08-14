"""Owner-approved player notification formatting."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from k_loto.application.notifications import ClaimedNotification
from k_loto.domain.enums import NotificationType

MOSCOW = ZoneInfo("Europe/Moscow")


def format_cas(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def _ticket_lines(tickets: list[dict[str, Any]], *, include_result: bool) -> str:
    sections: list[str] = []
    for ticket in tickets:
        number = int(ticket["public_number"])
        numbers = " • ".join(str(value) for value in ticket["numbers"])
        lines = [f"Билет {number:04d}", numbers]
        if include_result:
            lines.append(f"Совпадений: {int(ticket['matches'])}")
            lines.append(f"Выигрыш: {format_cas(int(ticket['prize']))} CAS")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def format_purchase_message(payload: dict[str, Any]) -> str:
    tickets = list(payload["tickets"])
    return (
        "K-Loto\n\n"
        "Билеты успешно куплены.\n\n"
        f"Лотерея: {payload['lottery_name']}\n"
        f"Тираж: {int(payload['draw_number']):04d}\n\n"
        f"{_ticket_lines(tickets, include_result=False)}\n\n"
        f"Списано: {format_cas(int(payload['total_cost']))} CAS\n"
        f"Баланс: {format_cas(int(payload['balance_after']))} CAS"
    )


def format_result_message(payload: dict[str, Any]) -> str:
    scheduled = datetime.fromisoformat(str(payload["scheduled_at"])).astimezone(MOSCOW)
    winning = " • ".join(str(value) for value in payload["winning_numbers"])
    tickets = list(payload["tickets"])
    return (
        "K-Loto — результат тиража\n\n"
        f"Лотерея: {payload['lottery_name']}\n"
        f"Тираж: {int(payload['draw_number']):04d}\n"
        f"Дата: {scheduled:%Y-%m-%d %H:%M} MSK\n"
        f"Выпавшие числа: {winning}\n\n"
        f"{_ticket_lines(tickets, include_result=True)}\n\n"
        f"Общий выигрыш: {format_cas(int(payload['total_prize']))} CAS\n"
        f"Баланс: {format_cas(int(payload['balance_after']))} CAS"
    )


class BotNotificationFormatter:
    def format(self, notification: ClaimedNotification) -> str:
        if notification.type == NotificationType.TICKET_PURCHASED:
            return format_purchase_message(notification.payload)
        if notification.type == NotificationType.DRAW_RESULT:
            return format_result_message(notification.payload)
        raise ValueError(f"Unsupported notification type: {notification.type}")
