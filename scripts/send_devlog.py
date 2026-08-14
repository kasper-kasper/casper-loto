"""Send one compact development notification to the configured Telegram chat."""

import argparse
from pathlib import Path

from scripts.env_file import load_env_file
from scripts.telegram_devlog import TelegramDevLogError, call_telegram


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True, help="Non-secret notification text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    values = load_env_file(Path(".env"))
    token = values.get("DEVLOG_BOT_TOKEN", "").strip()
    chat_id = values.get("DEVLOG_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("DEVLOG_BOT_TOKEN or DEVLOG_CHAT_ID is missing in .env.")
        return 2

    try:
        call_telegram(
            token,
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": args.message,
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
