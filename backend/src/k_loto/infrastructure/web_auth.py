"""Signed sessions and password credentials for the desktop Web client."""

import hmac
import json
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from k_loto.infrastructure.admin_auth import password_hash, verify_admin_password

WEB_COOKIE = "k_loto_web"
WEB_CSRF_HEADER = "X-Web-CSRF"


class InvalidWebSession(ValueError):
    """The browser-player session is malformed, expired or untrusted."""


@dataclass(frozen=True, slots=True)
class WebSession:
    account_id: UUID
    user_id: UUID
    csrf_token: str
    expires_at: datetime


def normalize_web_username(value: str) -> str:
    username = value.strip().casefold()
    if not 3 <= len(username) <= 128 or not all(
        char.isalnum() or char in "._-" for char in username
    ):
        raise ValueError("Логин: 3–128 символов, буквы, цифры, точка, _ или -.")
    return username


def hash_web_password(value: str) -> str:
    if not 8 <= len(value) <= 256:
        raise ValueError("Пароль должен содержать от 8 до 256 символов.")
    return password_hash.hash(value)


def verify_web_password(value: str, encoded_hash: str) -> bool:
    return verify_admin_password(value, encoded_hash)


def issue_web_session(
    account_id: UUID,
    user_id: UUID,
    secret: str,
    *,
    now: datetime | None = None,
    max_age_seconds: int = 604_800,
) -> tuple[str, WebSession]:
    if len(secret) < 32:
        raise ValueError("Web session secret must contain 32 characters.")
    timestamp = now or datetime.now(UTC)
    issued = WebSession(
        account_id,
        user_id,
        secrets.token_urlsafe(32),
        timestamp + timedelta(seconds=max_age_seconds),
    )
    payload = json.dumps(
        {
            "account_id": str(account_id),
            "csrf": issued.csrf_token,
            "expires_at": int(issued.expires_at.timestamp()),
            "purpose": "k-loto-web",
            "user_id": str(user_id),
            "version": 2,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    encoded = urlsafe_b64encode(payload).rstrip(b"=").decode()
    signature = hmac.new(secret.encode(), encoded.encode(), sha256).hexdigest()
    return f"{encoded}.{signature}", issued


def validate_web_session(
    token: str, secret: str, *, now: datetime | None = None
) -> WebSession:
    try:
        encoded, received = token.split(".", 1)
        expected = hmac.new(secret.encode(), encoded.encode(), sha256).hexdigest()
        if not hmac.compare_digest(received, expected):
            raise InvalidWebSession("Web session signature is invalid.")
        payload = json.loads(urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if payload.get("purpose") != "k-loto-web" or payload.get("version") != 2:
            raise InvalidWebSession("Web session purpose is invalid.")
        result = WebSession(
            UUID(str(payload["account_id"])),
            UUID(str(payload["user_id"])),
            str(payload["csrf"]),
            datetime.fromtimestamp(int(payload["expires_at"]), tz=UTC),
        )
    except InvalidWebSession:
        raise
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise InvalidWebSession("Web session is malformed.") from error
    if result.expires_at <= (now or datetime.now(UTC)):
        raise InvalidWebSession("Web session has expired.")
    return result
