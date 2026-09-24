"""Telegram Mini App initData authentication."""

import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from urllib.parse import parse_qsl


class InvalidTelegramInitData(ValueError):
    """Raised when Telegram Mini App authentication cannot be trusted."""


@dataclass(frozen=True, slots=True)
class TelegramWebAppUser:
    telegram_id: int
    username: str | None
    display_name: str


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    now: datetime | None = None,
    max_age_seconds: int = 3600,
) -> TelegramWebAppUser:
    """Validate Telegram's HMAC signature and return the authenticated user."""
    if not init_data or not bot_token:
        raise InvalidTelegramInitData("Telegram authentication is missing.")
    try:
        values = dict(parse_qsl(init_data, strict_parsing=True))
        received_hash = values.pop("hash")
        auth_date = int(values["auth_date"])
        raw_user = values["user"]
    except (KeyError, TypeError, ValueError) as error:
        raise InvalidTelegramInitData(
            "Telegram authentication is malformed."
        ) from error

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(values.items())
    )
    secret_key = hmac.new(
        key=b"WebAppData", msg=bot_token.encode(), digestmod=sha256
    ).digest()
    expected_hash = hmac.new(
        key=secret_key, msg=data_check_string.encode(), digestmod=sha256
    ).hexdigest()
    if not hmac.compare_digest(received_hash, expected_hash):
        raise InvalidTelegramInitData("Telegram authentication signature is invalid.")

    timestamp = now or datetime.now(UTC)
    authenticated_at = datetime.fromtimestamp(auth_date, tz=UTC)
    if authenticated_at > timestamp + timedelta(seconds=30):
        raise InvalidTelegramInitData("Telegram authentication date is in the future.")
    if authenticated_at < timestamp - timedelta(seconds=max_age_seconds):
        raise InvalidTelegramInitData("Telegram authentication has expired.")

    try:
        user = json.loads(raw_user)
        telegram_id = int(user["id"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise InvalidTelegramInitData("Telegram user data is malformed.") from error
    if telegram_id <= 0:
        raise InvalidTelegramInitData("Telegram user identity is invalid.")

    first_name = str(user.get("first_name") or "").strip()
    last_name = str(user.get("last_name") or "").strip()
    display_name = " ".join(value for value in (first_name, last_name) if value)
    username_value = user.get("username")
    username = str(username_value).strip() if username_value else None
    return TelegramWebAppUser(
        telegram_id=telegram_id,
        username=username,
        display_name=display_name or "Casper Loto Player",
    )
