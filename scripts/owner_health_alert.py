"""Private owner notifications independent of the API and PostgreSQL."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

if __package__:
    from scripts.server_maintenance import private_directory, write_state
else:
    from server_maintenance import private_directory, write_state


class RetryDelivery(Exception):
    """Telegram definitively rejected the request; retrying cannot duplicate it."""

    def __init__(self, delay: int = 300) -> None:
        self.delay = max(60, delay)


def credentials(root: Path) -> tuple[str, str]:
    values = {}
    for raw in (root / ".env.production").read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    token = values.get("LOTTERY_BOT_TOKEN", "")
    owner = values.get("OWNER_TELEGRAM_ID", "")
    if not token or not owner.isdecimal() or int(owner) <= 0:
        raise ValueError("Owner alert configuration unavailable")
    return token, owner


def send_message(config: tuple[str, str], text: str) -> None:
    token, owner = config
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": owner, "text": text}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read(16384))
    except HTTPError as error:
        if 400 <= error.code < 500:
            delay = 300
            if error.code == 429:
                try:
                    delay = int(
                        json.loads(error.read(16384))["parameters"]["retry_after"]
                    )
                except (ValueError, KeyError, TypeError):
                    pass
            raise RetryDelivery(delay) from None
        raise
    if payload.get("ok") is not True:
        raise RetryDelivery()


def deliver(
    warnings: list[str], path: Path, config: tuple[str, str], *, now: float
) -> str:
    """Caller serializes runs. Persist a claim before HTTP; never replay ambiguity."""
    state = json.loads(path.read_text()) if path.exists() else {}
    active = bool(warnings)
    previous = state.get("active", False)
    if active == previous and state.get("delivery") != "retry":
        return state.get("delivery", "idle")
    if active == previous and now < state.get("retry_at", 0):
        return "retry"
    state = {"active": active, "delivery": "uncertain", "attempted_at": now}
    write_state(path, state)
    descriptions = {
        "backup_missing_or_stale": "Нет резервной копии моложе 26 часов.",
        "backup_job_failed": "Задание резервного копирования завершилось ошибкой.",
        "backup_check_failed": "Не удалось проверить файлы резервных копий.",
        "backup_job_check_failed": "Не удалось проверить состояние задания backup.",
        "public_health_failed": "Мини-приложение не проходит проверку доступности.",
        "runtime_monitor_stale": "Нет свежего отчёта внутреннего мониторинга.",
        "scheduler_stale": "Планировщик давно не подтверждал успешную работу.",
        "overdue_draws": "Есть просроченные тиражи.",
        "delayed_publications": "Есть задержки доставки публикаций.",
        "disk_low": "На диске осталось мало свободного места.",
    }
    text = (
        "K-Loto: обнаружена техническая проблема.\n"
        + "\n".join(descriptions.get(code, code) for code in warnings)
        + "\nПроверь состояние сервера и резервных копий."
        if active
        else "K-Loto: восстановлено нормальное состояние. Сервисы доступны, "
        "резервная копия актуальна, проверка мониторинга пройдена."
    )
    try:
        send_message(config, text)
    except RetryDelivery as error:
        state.update(delivery="retry", retry_at=now + error.delay)
    except Exception:
        # Timeout/connection loss may follow successful delivery. No blind resend.
        pass
    else:
        state["delivery"] = "sent"
    write_state(path, state)
    return str(state["delivery"])


def notify(root: Path, warnings: list[str]) -> str:
    try:
        import fcntl

        directory = root / ".maintenance"
        private_directory(directory)
        path = directory / "owner-health-alert.json"
        lock = directory / "owner-health-alert.lock"
        if path.is_symlink() or lock.is_symlink():
            raise ValueError("Invalid alert state path")
        with lock.open("a") as stream:
            lock.chmod(0o600)
            fcntl.flock(stream, fcntl.LOCK_EX)
            return deliver(warnings, path, credentials(root), now=time.time())
    except Exception:
        # Never expose tokens, Telegram replies, recipient IDs or request URLs.
        return "unavailable"
