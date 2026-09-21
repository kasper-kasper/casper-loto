"""Signed administrator sessions and Argon2 password verification."""

import hmac
import json
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

ADMIN_COOKIE = "k_loto_admin"
ADMIN_CSRF_HEADER = "X-Admin-CSRF"
password_hash = PasswordHash.recommended()


class InvalidAdminSession(ValueError):
    """The administrator session is missing, malformed, expired or untrusted."""


@dataclass(frozen=True, slots=True)
class AdminSession:
    username: str
    csrf_token: str
    expires_at: datetime
    remembered: bool = False


def verify_admin_password(password: str, encoded_hash: str) -> bool:
    """Verify without leaking malformed-hash details to the transport layer."""
    try:
        return password_hash.verify(password, encoded_hash)
    except (ValueError, TypeError, UnknownHashError):
        return False


def issue_admin_session(
    username: str,
    secret: str,
    *,
    now: datetime | None = None,
    max_age_seconds: int = 28_800,
    remembered: bool = False,
) -> tuple[str, AdminSession]:
    if len(secret) < 32:
        raise ValueError("Administrator session secret must contain 32 characters.")
    timestamp = now or datetime.now(UTC)
    session = AdminSession(
        username=username,
        csrf_token=secrets.token_urlsafe(32),
        expires_at=timestamp + timedelta(seconds=max_age_seconds),
        remembered=remembered,
    )
    payload = json.dumps(
        {
            "csrf": session.csrf_token,
            "expires_at": int(session.expires_at.timestamp()),
            "purpose": "k-loto-admin",
            "remembered": session.remembered,
            "username": session.username,
            "version": 1,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    encoded = urlsafe_b64encode(payload).rstrip(b"=").decode()
    signature = hmac.new(secret.encode(), encoded.encode(), sha256).hexdigest()
    return f"{encoded}.{signature}", session


def validate_admin_session(
    token: str,
    secret: str,
    *,
    now: datetime | None = None,
) -> AdminSession:
    try:
        encoded, received_signature = token.split(".", 1)
        expected_signature = hmac.new(
            secret.encode(), encoded.encode(), sha256
        ).hexdigest()
        if not hmac.compare_digest(received_signature, expected_signature):
            raise InvalidAdminSession("Administrator session signature is invalid.")
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(urlsafe_b64decode(encoded + padding))
        if payload.get("purpose") != "k-loto-admin" or payload.get("version") != 1:
            raise InvalidAdminSession("Administrator session purpose is invalid.")
        expires_at = datetime.fromtimestamp(int(payload["expires_at"]), tz=UTC)
        username = str(payload["username"])
        csrf_token = str(payload["csrf"])
        remembered = bool(payload.get("remembered", False))
    except InvalidAdminSession:
        raise
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise InvalidAdminSession("Administrator session is malformed.") from error
    if expires_at <= (now or datetime.now(UTC)):
        raise InvalidAdminSession("Administrator session has expired.")
    if not username or not csrf_token:
        raise InvalidAdminSession("Administrator session identity is missing.")
    return AdminSession(username, csrf_token, expires_at, remembered)
