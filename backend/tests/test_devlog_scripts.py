"""Tests for secret-safe DevLog helpers."""

from pathlib import Path
from typing import Any

from scripts.env_file import load_env_file
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
