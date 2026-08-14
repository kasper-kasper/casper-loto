"""Tests for secret-safe DevLog helpers."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.env_file import load_env_file
from scripts.send_devlog import format_notification
from scripts.telegram_devlog import find_latest_chat_id


def test_load_env_file_handles_quotes_and_export(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\nexport DEVLOG_BOT_TOKEN='token-value'\nDEVLOG_CHAT_ID=123\n",
        encoding="utf-8",
    )

    assert load_env_file(env_file) == {
        "DEVLOG_BOT_TOKEN": "token-value",
        "DEVLOG_CHAT_ID": "123",
    }


def test_find_latest_chat_id() -> None:
    response: dict[str, Any] = {
        "result": [
            {"update_id": 1, "message": {"chat": {"id": 100}}},
            {"update_id": 2, "message": {"chat": {"id": -200}}},
        ]
    }

    assert find_latest_chat_id(response) == -200


def test_release_notification_contains_required_fields() -> None:
    message = format_notification(
        message_type="DEVLOG",
        version="0.2.0",
        commit="abc1234",
        tests="11 passed",
        message="Сделано: модель тиражей.",
        timestamp=datetime(2026, 8, 14, 20, 30, tzinfo=UTC),
    )

    assert "K-Loto v0.2.0 — DEVLOG" in message
    assert "2026-08-14 23:30 MSK" in message
    assert "Commit: abc1234" in message
    assert "Tests: 11 passed" in message
