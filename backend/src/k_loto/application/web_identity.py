"""Browser credentials and single-use Telegram login, sharing existing users."""

import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.welcome import WelcomeGrantService
from k_loto.infrastructure.database.models import (
    Balance,
    User,
    UserNotificationPreference,
    WebAccount,
    WebLoginToken,
)
from k_loto.infrastructure.web_auth import hash_web_password, normalize_web_username


class WebIdentityError(ValueError):
    """An authentication or binding attempt cannot be completed."""


class WebIdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(self, username: str, password: str) -> tuple[WebAccount, User]:
        username = normalize_web_username(username)
        encoded = hash_web_password(password)
        async with self.session.begin():
            user = User(
                id=uuid4(), display_name=username, is_active=True, is_admin=False
            )
            self.session.add(user)
            await self.session.flush()
            account = WebAccount(
                id=uuid4(),
                user_id=user.id,
                username=username,
                password_hash=encoded,
                is_active=True,
            )
            self.session.add_all(
                [
                    account,
                    Balance(user_id=user.id, amount=0, version=1),
                    UserNotificationPreference(user_id=user.id),
                ]
            )
            await self.session.flush()
            await WelcomeGrantService.ensure_in_transaction(self.session, user.id)
        return account, user

    async def issue_telegram_code(self, user_id: UUID) -> str:
        code = secrets.token_hex(8).upper()
        now = datetime.now(UTC)
        async with self.session.begin():
            user = await self.session.scalar(
                select(User).where(User.id == user_id).with_for_update()
            )
            if user is None or not user.is_active or user.is_admin:
                raise WebIdentityError("Вход для этого профиля недоступен.")
            await self.session.execute(
                update(WebLoginToken)
                .where(
                    WebLoginToken.user_id == user_id, WebLoginToken.used_at.is_(None)
                )
                .values(used_at=now)
            )
            self.session.add(
                WebLoginToken(
                    user_id=user_id,
                    token_hash=sha256(code.encode()).hexdigest(),
                    expires_at=now + timedelta(minutes=5),
                )
            )
        return code

    async def redeem_telegram_code(self, code: str) -> User:
        normalized = code.strip().replace(" ", "").upper()
        now = datetime.now(UTC)
        async with self.session.begin():
            token = await self.session.scalar(
                select(WebLoginToken)
                .where(
                    WebLoginToken.token_hash == sha256(normalized.encode()).hexdigest()
                )
                .with_for_update()
            )
            if token is None or token.used_at is not None or token.expires_at <= now:
                raise WebIdentityError("Код неверный или истёк. Получите новый в боте.")
            user = await self.session.scalar(
                select(User).where(User.id == token.user_id)
            )
            if (
                user is None
                or not user.is_active
                or user.is_admin
                or not user.telegram_id
            ):
                raise WebIdentityError("Вход для этого профиля недоступен.")
            token.used_at = now
        return user

    async def add_password(self, user_id: UUID, username: str, password: str) -> None:
        username = normalize_web_username(username)
        encoded = hash_web_password(password)
        async with self.session.begin():
            user = await self.session.scalar(
                select(User).where(User.id == user_id).with_for_update()
            )
            if user is None or not user.is_active or user.is_admin:
                raise WebIdentityError("Профиль недоступен.")
            if await self.session.scalar(
                select(WebAccount.id).where(WebAccount.user_id == user_id)
            ):
                raise WebIdentityError("У этого профиля уже есть логин и пароль.")
            self.session.add(
                WebAccount(
                    id=uuid4(),
                    user_id=user_id,
                    username=username,
                    password_hash=encoded,
                    is_active=True,
                )
            )
