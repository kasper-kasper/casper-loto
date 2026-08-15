"""Secure one-click transition from a private Telegram chat to player Web."""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.infrastructure.database.models import User, WebLoginToken


@dataclass(frozen=True, slots=True)
class IssuedWebLogin:
    token: str
    expires_at: datetime


class TelegramWebLoginService:
    """Issue and atomically consume short-lived, one-time login tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def issue(
        self,
        telegram_id: int,
        *,
        max_age_seconds: int = 300,
        now: datetime | None = None,
    ) -> IssuedWebLogin:
        timestamp = now or datetime.now(UTC)
        raw_token = secrets.token_urlsafe(32)
        expires_at = timestamp + timedelta(seconds=max_age_seconds)
        async with self._session.begin():
            user = await self._session.scalar(
                select(User).where(
                    User.telegram_id == telegram_id,
                    User.is_active.is_(True),
                    User.is_admin.is_(False),
                )
            )
            if user is None:
                raise LookupError("Telegram player does not exist.")
            self._session.add(
                WebLoginToken(
                    id=uuid4(),
                    user_id=user.id,
                    token_hash=_token_hash(raw_token),
                    expires_at=expires_at,
                )
            )
        return IssuedWebLogin(raw_token, expires_at)

    async def consume(
        self, raw_token: str, *, now: datetime | None = None
    ) -> User | None:
        if not 32 <= len(raw_token) <= 128:
            return None
        timestamp = now or datetime.now(UTC)
        async with self._session.begin():
            login = await self._session.scalar(
                select(WebLoginToken)
                .where(WebLoginToken.token_hash == _token_hash(raw_token))
                .with_for_update()
            )
            if (
                login is None
                or login.used_at is not None
                or login.expires_at <= timestamp
            ):
                return None
            user = await self._session.scalar(
                select(User).where(
                    User.id == login.user_id,
                    User.is_active.is_(True),
                    User.is_admin.is_(False),
                )
            )
            if user is None:
                return None
            login.used_at = timestamp
        return user


def _token_hash(raw_token: str) -> str:
    return sha256(raw_token.encode()).hexdigest()
