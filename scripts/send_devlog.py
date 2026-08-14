"""Send one compact development notification to the configured Telegram chat."""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from scripts.env_file import load_env_file
from scripts.telegram_devlog import TelegramDevLogError, call_telegram


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", required=True, choices=("CHANGELOG", "DEVLOG"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tests", required=True)
    parser.add_argument("--message", required=True, help="Non-secret notification body")
    return parser.parse_args()


def format_notification(
    *,
    message_type: Literal["CHANGELOG", "DEVLOG"],
    version: str,
    commit: str,
    tests: str,
    message: str,
    timestamp: datetime | None = None,
) -> str:
    """Build the standardized owner-facing release notification."""
    moscow = ZoneInfo("Europe/Moscow")
    current = (timestamp or datetime.now(moscow)).astimezone(moscow)
    icon = "📦" if message_type == "CHANGELOG" else "🛠"
    return (
        f"{icon} K-Loto v{version} — {message_type}\n\n"
        f"Дата: {current:%Y-%m-%d %H:%M} MSK\n\n"
        f"{message.strip()}\n\n"
        f"Commit: {commit}\n"
        f"Tests: {tests}"
    )


def main() -> int:
    args = parse_args()
    values = load_env_file(Path(".env"))
    token = values.get("DEVLOG_BOT_TOKEN", "").strip()
    chat_id = values.get("DEVLOG_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("DEVLOG_BOT_TOKEN or DEVLOG_CHAT_ID is missing in .env.")
        return 2

    try:
        text = format_notification(
            message_type=args.type,
            version=args.version,
            commit=args.commit,
            tests=args.tests,
            message=args.message,
        )
        call_telegram(
            token,
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": "true",
            },
        )
    except TelegramDevLogError as exc:
        print(str(exc))
        return 1

    print("DevLog notification sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
