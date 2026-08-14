"""FastAPI dependencies shared by transport handlers."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.dev_mode import DevBootstrapConfig, DevBootstrapService
from k_loto.application.identity import TelegramIdentityService
from k_loto.core.config import Settings, get_settings
from k_loto.infrastructure.database.session import session_factory
from k_loto.infrastructure.local_dev_auth import (
    LOCAL_DEV_COOKIE,
    InvalidLocalDevSession,
    is_loopback_authority,
    is_loopback_host,
    is_loopback_origin,
    validate_local_dev_session,
)
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


async def _authenticate_telegram(
    init_data: str, session: AsyncSession, settings: Settings
) -> CurrentMiniAppUser:
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


async def get_current_miniapp_user(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request,
    init_data: Annotated[str | None, Header(alias="X-Telegram-Init-Data")] = None,
    local_dev_session: Annotated[str | None, Cookie(alias=LOCAL_DEV_COOKIE)] = None,
) -> CurrentMiniAppUser:
    """Authenticate with Telegram, or a loopback-only development cookie."""
    if init_data:
        return await _authenticate_telegram(init_data, session, settings)
    if not settings.local_dev_auth_available or local_dev_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram authentication is missing.",
        )
    client_host = request.client.host if request.client else None
    origin = request.headers.get("origin")
    if (
        not is_loopback_host(client_host)
        or not is_loopback_authority(request.headers.get("host"))
        or (origin is not None and not is_loopback_origin(origin))
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local development authentication is restricted to loopback.",
        )
    secret = settings.miniapp_dev_session_secret
    if secret is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        validate_local_dev_session(local_dev_session, secret.get_secret_value())
    except InvalidLocalDevSession as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Local development session is invalid or expired.",
        ) from error
    profile = await TelegramIdentityService(session).bind(
        telegram_id=settings.miniapp_dev_user_telegram_id,
        username="local_dev_player",
        display_name="Local Test Player",
    )
    await DevBootstrapService(
        session,
        DevBootstrapConfig(
            initial_user_balance=settings.miniapp_dev_initial_balance,
            weekly_ticket_price=settings.miniapp_dev_weekly_ticket_price,
            weekly_base_jackpot=settings.miniapp_dev_weekly_base_jackpot,
            weekly_reserve=settings.miniapp_dev_weekly_reserve,
        ),
    ).ensure(profile.id, now=datetime.now(UTC))
    return CurrentMiniAppUser(profile.id, settings.miniapp_dev_user_telegram_id)
