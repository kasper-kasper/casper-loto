"""FastAPI dependencies shared by transport handlers."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.identity import TelegramIdentityService
from k_loto.core.config import Settings, get_settings
from k_loto.infrastructure.database.session import session_factory
from k_loto.infrastructure.telegram_auth import (
    InvalidTelegramInitData,
    validate_init_data,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield one database session per request."""
    async with session_factory() as session:
        yield session


@dataclass(frozen=True, slots=True)
class CurrentMiniAppUser:
    id: UUID
    telegram_id: int


async def get_current_miniapp_user(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    init_data: Annotated[str | None, Header(alias="X-Telegram-Init-Data")] = None,
) -> CurrentMiniAppUser:
    """Authenticate Telegram initData and bind it to a backend user."""
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram authentication is missing.",
        )
    if settings.lottery_bot_token is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram authentication is not configured.",
        )
    try:
        telegram_user = validate_init_data(
            init_data,
            settings.lottery_bot_token.get_secret_value(),
            max_age_seconds=settings.telegram_init_data_max_age_seconds,
        )
    except InvalidTelegramInitData as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram authentication is invalid or expired.",
        ) from error
    profile = await TelegramIdentityService(session).bind(
        telegram_id=telegram_user.telegram_id,
        username=telegram_user.username,
        display_name=telegram_user.display_name,
    )
    return CurrentMiniAppUser(profile.id, telegram_user.telegram_id)
