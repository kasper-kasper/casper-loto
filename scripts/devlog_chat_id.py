"""Discover DEVLOG_CHAT_ID after the owner sends the bot a message."""

from pathlib import Path

from scripts.env_file import load_env_file
from scripts.telegram_devlog import (
    TelegramDevLogError,
    call_telegram,
    find_latest_chat_id,
)


def main() -> int:
    values = load_env_file(Path(".env"))
    token = values.get("DEVLOG_BOT_TOKEN", "").strip()
    if not token:
        print("DEVLOG_BOT_TOKEN is missing or empty in .env.")
        return 2

    try:
        result = call_telegram(token, "getUpdates", {"limit": "20", "timeout": "0"})
    except TelegramDevLogError as exc:
        print(str(exc))
        return 1

    chat_id = find_latest_chat_id(result)
    if chat_id is None:
        print("No incoming message found. Send the DevLog bot a message and retry.")
        return 3

    print(f"DEVLOG_CHAT_ID={chat_id}")
    print("Copy this line into .env. Do not commit .env.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
