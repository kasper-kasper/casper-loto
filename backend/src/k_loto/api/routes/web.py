"""Ordinary browser client API with password and cookie authentication."""

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.api.dependencies import get_db_session
from k_loto.api.routes.miniapp import (
    DashboardResponse,
    PurchaseRequest,
    PurchaseResponse,
    TicketListResponse,
    _dashboard_response,
    _ticket_response,
)
from k_loto.application.daily import DailyTicketPurchaseService
from k_loto.application.miniapp import MiniAppQueryService
from k_loto.application.web_login import TelegramWebLoginService
from k_loto.application.weekly import WeeklyTicketPurchaseService
from k_loto.core.config import Settings, get_settings
from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InvalidTicket,
    NoAvailableDraw,
)
from k_loto.infrastructure.database.models import User, WebAccount
from k_loto.infrastructure.web_auth import (
    WEB_COOKIE,
    WEB_CSRF_HEADER,
    InvalidWebSession,
    WebSession,
    issue_web_session,
    normalize_web_username,
    validate_web_session,
    verify_web_password,
)

router = APIRouter(prefix="/api/v1/web", tags=["web"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class TelegramLoginRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)


class SessionResponse(BaseModel):
    display_name: str
    csrf_token: str
    expires_at: datetime


class DrawResultResponse(BaseModel):
    lottery_code: str
    lottery_name: str
    draw_number: int
    scheduled_at: datetime
    executed_at: datetime | None
    winning_numbers: list[int]
    ticket_count: int
    total_payout: int


class ResultsResponse(BaseModel):
    draws: list[DrawResultResponse]


@dataclass(frozen=True, slots=True)
class CurrentWebPlayer:
    user_id: UUID
    display_name: str
    session: WebSession


def _secret(settings: Settings) -> str:
    if not settings.web_auth_available or settings.web_session_secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web authentication is not configured.",
        )
    return settings.web_session_secret.get_secret_value()


async def current_web_player(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    token: Annotated[str | None, Cookie(alias=WEB_COOKIE)] = None,
) -> CurrentWebPlayer:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        web_session = validate_web_session(token, _secret(settings))
    except InvalidWebSession as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from error
    if web_session.account_id is None:
        user = await session.scalar(
            select(User).where(
                User.id == web_session.user_id,
                User.is_active.is_(True),
                User.is_admin.is_(False),
            )
        )
    else:
        row = (
            await session.execute(
                select(WebAccount, User)
                .join(User, User.id == WebAccount.user_id)
                .where(
                    WebAccount.id == web_session.account_id,
                    WebAccount.user_id == web_session.user_id,
                    WebAccount.is_active.is_(True),
                    User.is_active.is_(True),
                    User.is_admin.is_(False),
                )
            )
        ).one_or_none()
        user = row[1] if row is not None else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return CurrentWebPlayer(user.id, user.display_name, web_session)


async def web_player_with_csrf(
    player: Annotated[CurrentWebPlayer, Depends(current_web_player)],
    csrf: Annotated[str | None, Header(alias=WEB_CSRF_HEADER)] = None,
) -> CurrentWebPlayer:
    if csrf is None or not hmac.compare_digest(csrf, player.session.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token."
        )
    return player


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        WEB_COOKIE,
        token,
        max_age=settings.web_session_max_age_seconds,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        path="/api/v1/web",
    )


def _session_response(display_name: str, issued: WebSession) -> SessionResponse:
    return SessionResponse(
        display_name=display_name,
        csrf_token=issued.csrf_token,
        expires_at=issued.expires_at,
    )


@router.post("/auth/login", response_model=SessionResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    try:
        username = normalize_web_username(payload.username)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from error
    row = (
        await session.execute(
            select(WebAccount, User)
            .join(User, User.id == WebAccount.user_id)
            .where(WebAccount.username == username)
        )
    ).one_or_none()
    if (
        row is None
        or not row[0].is_active
        or not row[1].is_active
        or row[1].is_admin
        or not verify_web_password(payload.password, row[0].password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    account, user = row
    token, issued = issue_web_session(
        account.id,
        user.id,
        _secret(settings),
        max_age_seconds=settings.web_session_max_age_seconds,
    )
    account.last_login_at = datetime.now(UTC)
    await session.commit()
    _set_session_cookie(response, token, settings)
    return _session_response(user.display_name, issued)


@router.post("/auth/telegram", response_model=SessionResponse)
async def telegram_login(
    payload: TelegramLoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    """Exchange a one-time token delivered in a private bot chat for a cookie."""
    user = await TelegramWebLoginService(session).consume(payload.token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ссылка устарела или уже использована. Получите новую в боте.",
        )
    token, issued = issue_web_session(
        None,
        user.id,
        _secret(settings),
        max_age_seconds=settings.web_session_max_age_seconds,
    )
    _set_session_cookie(response, token, settings)
    return _session_response(user.display_name, issued)


@router.get("/auth/session", response_model=SessionResponse)
async def auth_session(
    player: Annotated[CurrentWebPlayer, Depends(current_web_player)],
) -> SessionResponse:
    return SessionResponse(
        display_name=player.display_name,
        csrf_token=player.session.csrf_token,
        expires_at=player.session.expires_at,
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    _player: Annotated[CurrentWebPlayer, Depends(web_player_with_csrf)],
) -> None:
    response.delete_cookie(WEB_COOKIE, path="/api/v1/web")


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    player: Annotated[CurrentWebPlayer, Depends(current_web_player)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardResponse:
    return _dashboard_response(
        await MiniAppQueryService(session).dashboard(player.user_id)
    )


@router.get("/tickets", response_model=TicketListResponse)
async def tickets(
    player: Annotated[CurrentWebPlayer, Depends(current_web_player)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    state: Annotated[Literal["active", "history"], Query()] = "active",
) -> TicketListResponse:
    items = await MiniAppQueryService(session).tickets(
        player.user_id, active=state == "active"
    )
    return TicketListResponse(tickets=[_ticket_response(item) for item in items])


@router.get("/results", response_model=ResultsResponse)
async def results(
    _player: Annotated[CurrentWebPlayer, Depends(current_web_player)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResultsResponse:
    draws = await MiniAppQueryService(session).results()
    return ResultsResponse(
        draws=[
            DrawResultResponse(
                lottery_code=item.lottery_code,
                lottery_name=item.lottery_name,
                draw_number=item.draw_number,
                scheduled_at=item.scheduled_at,
                executed_at=item.executed_at,
                winning_numbers=list(item.winning_numbers),
                ticket_count=item.ticket_count,
                total_payout=item.total_payout,
            )
            for item in draws
        ]
    )


@router.post(
    "/weekly/purchases",
    response_model=PurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def purchase(
    payload: PurchaseRequest,
    player: Annotated[CurrentWebPlayer, Depends(web_player_with_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PurchaseResponse:
    try:
        result = await WeeklyTicketPurchaseService(session).purchase(
            user_id=player.user_id,
            combinations=[list(value) for value in payload.combinations],
            idempotency_key=payload.idempotency_key,
        )
    except InsufficientBalance as error:
        raise HTTPException(
            status_code=402, detail="Insufficient CAS balance."
        ) from error
    except InvalidTicket as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except NoAvailableDraw as error:
        raise HTTPException(
            status_code=409, detail="No Weekly draw is open."
        ) from error
    except ConfigurationError as error:
        raise HTTPException(
            status_code=503, detail="Weekly is not configured."
        ) from error
    return PurchaseResponse(
        operation_id=result.operation_id,
        draw_id=result.draw_id,
        ticket_ids=list(result.ticket_ids),
        total_cost=result.total_cost,
        balance_after=result.balance_after,
        already_processed=result.already_processed,
    )


@router.post(
    "/daily/purchases",
    response_model=PurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def purchase_daily(
    payload: PurchaseRequest,
    player: Annotated[CurrentWebPlayer, Depends(web_player_with_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PurchaseResponse:
    try:
        result = await DailyTicketPurchaseService(session).purchase(
            user_id=player.user_id,
            combinations=[list(value) for value in payload.combinations],
            idempotency_key=payload.idempotency_key,
        )
    except InsufficientBalance as error:
        raise HTTPException(
            status_code=402, detail="Insufficient CAS balance."
        ) from error
    except InvalidTicket as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except NoAvailableDraw as error:
        raise HTTPException(status_code=409, detail="No Daily draw is open.") from error
    except ConfigurationError as error:
        raise HTTPException(
            status_code=503, detail="Daily is not configured."
        ) from error
    return PurchaseResponse(
        operation_id=result.operation_id,
        draw_id=result.draw_id,
        ticket_ids=list(result.ticket_ids),
        total_cost=result.total_cost,
        balance_after=result.balance_after,
        already_processed=result.already_processed,
    )
