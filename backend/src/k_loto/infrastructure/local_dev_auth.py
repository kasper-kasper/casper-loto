"""Loopback-only signed browser sessions for local Mini App development."""

import hmac
import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from ipaddress import ip_address
from urllib.parse import urlparse

LOCAL_DEV_COOKIE = "k_loto_local_dev"


class InvalidLocalDevSession(ValueError):
    """The local development browser session cannot be trusted."""


def is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def is_loopback_origin(origin: str | None) -> bool:
    if not origin:
        return False
    parsed = urlparse(origin)
    return parsed.scheme in {"http", "https"} and is_loopback_host(parsed.hostname)


def is_loopback_authority(authority: str | None) -> bool:
    if not authority:
        return False
    return is_loopback_host(urlparse(f"//{authority}").hostname)


def issue_local_dev_session(
    secret: str,
    *,
    now: datetime | None = None,
    max_age_seconds: int = 28_800,
) -> str:
    if len(secret) < 32:
        raise ValueError("Local development session secret must contain 32 characters.")
    timestamp = now or datetime.now(UTC)
    payload = json.dumps(
        {
            "expires_at": int(
                (timestamp + timedelta(seconds=max_age_seconds)).timestamp()
            ),
            "purpose": "k-loto-local-dev",
            "version": 1,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    encoded = urlsafe_b64encode(payload).rstrip(b"=").decode()
    signature = hmac.new(secret.encode(), encoded.encode(), sha256).hexdigest()
    return f"{encoded}.{signature}"


def validate_local_dev_session(
    token: str,
    secret: str,
    *,
    now: datetime | None = None,
) -> None:
    try:
        encoded, received_signature = token.split(".", 1)
        expected_signature = hmac.new(
            secret.encode(), encoded.encode(), sha256
        ).hexdigest()
        if not hmac.compare_digest(received_signature, expected_signature):
            raise InvalidLocalDevSession("Local development session is invalid.")
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(urlsafe_b64decode(encoded + padding))
        if payload.get("purpose") != "k-loto-local-dev" or payload.get("version") != 1:
            raise InvalidLocalDevSession(
                "Local development session purpose is invalid."
            )
        expires_at = datetime.fromtimestamp(int(payload["expires_at"]), tz=UTC)
    except InvalidLocalDevSession:
        raise
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise InvalidLocalDevSession(
            "Local development session is malformed."
        ) from error
    if expires_at <= (now or datetime.now(UTC)):
        raise InvalidLocalDevSession("Local development session has expired.")
