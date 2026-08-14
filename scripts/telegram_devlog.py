"""Safe Telegram DevLog API helpers."""

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any


class TelegramDevLogError(RuntimeError):
    """A redacted Telegram integration failure."""


def call_telegram(
    token: str,
    method: str,
    payload: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Call Telegram without exposing the token or response body in errors."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(payload or {}).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise TelegramDevLogError(
            f"Telegram API rejected the request (HTTP {exc.code})."
        ) from None
    except (urllib.error.URLError, TimeoutError):
        raise TelegramDevLogError("Telegram API is unavailable.") from None

    try:
        result = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise TelegramDevLogError(
            "Telegram API returned an invalid response."
        ) from None
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise TelegramDevLogError("Telegram API rejected the request.")
    return result


def find_latest_chat_id(result: Mapping[str, Any]) -> int | None:
    """Extract the latest message chat ID from a getUpdates response."""
    updates = result.get("result")
    if not isinstance(updates, list):
        return None

    for update in reversed(updates):
        if not isinstance(update, dict):
            continue
        for field in ("message", "channel_post", "edited_message"):
            message = update.get(field)
            if not isinstance(message, dict):
                continue
            chat = message.get("chat")
            if isinstance(chat, dict):
                chat_id = chat.get("id")
                if isinstance(chat_id, int):
                    return chat_id
    return None
