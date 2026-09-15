"""Desktop browser client API with simple password authentication."""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.api.dependencies import get_db_session
from k_loto.api.routes.miniapp import (
    AccountResponse,
    BingoPurchaseRequest,
    DashboardResponse,
    LiveFeedResponse,
    PurchaseRequest,
    PurchaseResponse,
    TicketListResponse,
    _dashboard_response,
    _live_response,
    _ticket_response,
)
from k_loto.application.bingo import BingoQueryService
from k_loto.application.miniapp import MiniAppQueryService
from k_loto.application.weekly import LotteryTicketPurchaseService, PurchaseResult
from k_loto.application.welcome import WelcomeGrantService
from k_loto.core.config import Settings, get_settings
from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InvalidTicket,
    NoAvailableDraw,
)
from k_loto.infrastructure.database.models import (
    Balance,
    User,
    UserNotificationPreference,
    WebAccount,
)
from k_loto.infrastructure.rate_limit import purchase_rate_limiter
from k_loto.infrastructure.web_auth import (
    WEB_COOKIE,
    WEB_CSRF_HEADER,
    InvalidWebSession,
    WebSession,
    hash_web_password,
    issue_web_session,
    normalize_web_username,
    validate_web_session,
    verify_web_password,
)

router = APIRouter(prefix="/api/v1/web", tags=["web"])


class CredentialsRequest(BaseModel):
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=8, max_length=256)


class SessionResponse(BaseModel):
    display_name: str
    csrf_token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class CurrentWebPlayer:
    user_id: UUID
    display_name: str
    session: WebSession


def _secret(settings: Settings) -> str:
    if not settings.web_auth_available or settings.web_session_secret is None:
        raise HTTPException(status_code=503, detail="Web-версия временно недоступна.")
    return settings.web_session_secret.get_secret_value()


def _set_cookie(response: Response, token: str, settings: Settings) -> None:
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


async def current_web_player(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    token: Annotated[str | None, Cookie(alias=WEB_COOKIE)] = None,
) -> CurrentWebPlayer:
    if token is None:
        raise HTTPException(status_code=401)
    try:
        web_session = validate_web_session(token, _secret(settings))
    except InvalidWebSession as error:
        raise HTTPException(status_code=401) from error
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
    if row is None:
        raise HTTPException(status_code=401)
    return CurrentWebPlayer(row[1].id, row[1].display_name, web_session)


async def web_player_with_csrf(
    player: Annotated[CurrentWebPlayer, Depends(current_web_player)],
    csrf: Annotated[str | None, Header(alias=WEB_CSRF_HEADER)] = None,
) -> CurrentWebPlayer:
    if csrf is None or not hmac.compare_digest(csrf, player.session.csrf_token):
        raise HTTPException(
            status_code=403, detail="Сессия устарела. Обновите страницу."
        )
    return player


async def _issue_login(
    account: WebAccount, user: User, response: Response, settings: Settings
) -> SessionResponse:
    token, issued = issue_web_session(
        account.id,
        user.id,
        _secret(settings),
        max_age_seconds=settings.web_session_max_age_seconds,
    )
    _set_cookie(response, token, settings)
    return _session_response(user.display_name, issued)


@router.post("/auth/register", response_model=SessionResponse, status_code=201)
async def register(
    payload: CredentialsRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    try:
        username = normalize_web_username(payload.username)
        encoded = hash_web_password(payload.password)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    user = User(
        id=uuid4(),
        telegram_id=None,
        username=None,
        display_name=username,
        is_active=True,
        is_admin=False,
    )
    account = WebAccount(
        id=uuid4(),
        user_id=user.id,
        username=username,
        password_hash=encoded,
        is_active=True,
    )
    try:
        async with session.begin():
            if await session.scalar(
                select(WebAccount.id).where(WebAccount.username == username)
            ):
                raise HTTPException(status_code=409, detail="Такой логин уже занят.")
            session.add(user)
            await session.flush()
            session.add_all(
                [
                    Balance(user_id=user.id, amount=0, version=1),
                    UserNotificationPreference(user_id=user.id),
                    account,
                ]
            )
            await session.flush()
            await WelcomeGrantService.ensure_in_transaction(session, user.id)
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="Такой логин уже занят.") from error
    return await _issue_login(account, user, response, settings)


@router.post("/auth/login", response_model=SessionResponse)
async def login(
    payload: CredentialsRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    try:
        username = normalize_web_username(payload.username)
    except ValueError as error:
        raise HTTPException(
            status_code=401, detail="Неверный логин или пароль."
        ) from error
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
        or not verify_web_password(payload.password, row[0].password_hash)
    ):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль.")
    row[0].last_login_at = datetime.now(UTC)
    await session.commit()
    return await _issue_login(row[0], row[1], response, settings)


@router.get("/auth/session", response_model=SessionResponse)
async def auth_session(
    player: Annotated[CurrentWebPlayer, Depends(current_web_player)],
) -> SessionResponse:
    return _session_response(player.display_name, player.session)


@router.post("/auth/logout", status_code=204)
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


@router.get("/account", response_model=AccountResponse)
async def account(
    player: Annotated[CurrentWebPlayer, Depends(current_web_player)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountResponse:
    item = await MiniAppQueryService(session).account(player.user_id)
    return AccountResponse(
        display_name=item.display_name,
        balance=item.balance,
        ticket_count=item.ticket_count,
        active_ticket_count=item.active_ticket_count,
        winning_ticket_count=item.winning_ticket_count,
        total_spent=item.total_spent,
        total_won=item.total_won,
        best_win=item.best_win,
        favorite_lottery_code=item.favorite_lottery_code,
        favorite_lottery_name=item.favorite_lottery_name,
        favorite_numbers=list(item.favorite_numbers),
        unread_notification_count=item.unread_notification_count,
        notification_preferences={
            "telegram_enabled": item.notification_preferences.telegram_enabled,
            "draw_results_enabled": item.notification_preferences.draw_results_enabled,
            "inactivity_reminders_enabled": (
                item.notification_preferences.inactivity_reminders_enabled
            ),
        },
    )


@router.get("/tickets", response_model=TicketListResponse)
async def tickets(
    player: Annotated[CurrentWebPlayer, Depends(current_web_player)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    state: Annotated[Literal["active", "history"], Query()] = "active",
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TicketListResponse:
    service = MiniAppQueryService(session)
    items = await service.tickets(
        player.user_id, active=state == "active", limit=limit, offset=offset
    )
    total = await service.ticket_count(player.user_id, active=state == "active")
    return TicketListResponse(
        tickets=[_ticket_response(item) for item in items],
        total=total,
        has_more=offset + len(items) < total,
    )


@router.get("/live", response_model=LiveFeedResponse)
async def live(
    player: Annotated[CurrentWebPlayer, Depends(current_web_player)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    scope: Annotated[Literal["standard", "fast"], Query()] = "standard",
    lottery_code: Annotated[str | None, Query(max_length=32)] = None,
) -> LiveFeedResponse:
    return _live_response(
        await MiniAppQueryService(session).live(
            player.user_id, fast_only=scope == "fast", lottery_code=lottery_code
        )
    )


@router.get("/bingo/inventory")
async def bingo_inventory(
    _player: Annotated[CurrentWebPlayer, Depends(current_web_player)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    offset: Annotated[int, Query(ge=0, le=2000)] = 0,
    number: Annotated[list[int] | None, Query()] = None,
) -> dict[str, object]:
    try:
        return await BingoQueryService(session).inventory(
            offset=offset, required_numbers=tuple(number or ())
        )
    except InvalidTicket as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _purchase_response(result: PurchaseResult) -> PurchaseResponse:
    return PurchaseResponse(
        operation_id=result.operation_id,
        draw_id=result.draw_id,
        draw_ids=list(result.draw_ids or (result.draw_id,)),
        draw_count=result.draw_count,
        ticket_ids=list(result.ticket_ids),
        total_cost=result.total_cost,
        balance_after=result.balance_after,
        already_processed=result.already_processed,
    )


async def _purchase(
    lottery_code: str,
    payload: PurchaseRequest,
    player: CurrentWebPlayer,
    session: AsyncSession,
    settings: Settings,
) -> PurchaseResponse:
    if not purchase_rate_limiter.allow(
        player.user_id, limit=settings.miniapp_purchase_requests_per_minute
    ):
        raise HTTPException(
            status_code=429, detail="Слишком много попыток. Подождите 5 секунд."
        )
    try:
        result = await LotteryTicketPurchaseService(
            session, lottery_code=lottery_code
        ).purchase(
            user_id=player.user_id,
            combinations=[list(value) for value in payload.combinations],
            idempotency_key=payload.idempotency_key,
            draw_count=payload.draw_count,
        )
    except InsufficientBalance as error:
        raise HTTPException(status_code=402, detail="Недостаточно CAS.") from error
    except InvalidTicket as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except NoAvailableDraw as error:
        raise HTTPException(
            status_code=409, detail="Продажи на этот тираж закрыты."
        ) from error
    except ConfigurationError as error:
        raise HTTPException(
            status_code=503, detail="Лотерея временно недоступна."
        ) from error
    return _purchase_response(result)


@router.post(
    "/lotteries/{lottery_code}/purchases",
    response_model=PurchaseResponse,
    status_code=201,
)
async def purchase_lottery(
    lottery_code: str,
    payload: PurchaseRequest,
    player: Annotated[CurrentWebPlayer, Depends(web_player_with_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session, use_cache=False)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PurchaseResponse:
    return await _purchase(lottery_code, payload, player, session, settings)


@router.post("/bingo/purchases", response_model=PurchaseResponse, status_code=201)
async def purchase_bingo(
    payload: BingoPurchaseRequest,
    player: Annotated[CurrentWebPlayer, Depends(web_player_with_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session, use_cache=False)],
) -> PurchaseResponse:
    if bool(payload.ticket_ids) == (payload.quantity is not None):
        raise HTTPException(
            status_code=422, detail="Choose ticket IDs or a quick-purchase quantity."
        )
    if len(set(payload.required_numbers)) != len(payload.required_numbers) or any(
        not 1 <= number <= 60 for number in payload.required_numbers
    ):
        raise HTTPException(
            status_code=422, detail="Choose distinct numbers from 1 to 60."
        )
    quantity = len(payload.ticket_ids) or payload.quantity or 0
    try:
        result = await LotteryTicketPurchaseService(
            session, "bingo", target_draw_id=payload.draw_id
        ).purchase(
            user_id=player.user_id,
            combinations=[[] for _ in range(quantity)],
            pool_ticket_ids=payload.ticket_ids or None,
            pool_required_numbers=tuple(payload.required_numbers),
            select_bingo_pool=not payload.ticket_ids,
            idempotency_key=hashlib.sha256(
                f"bingo:{player.user_id}:{payload.idempotency_key}".encode()
            ).hexdigest(),
        )
    except (
        InsufficientBalance,
        InvalidTicket,
        NoAvailableDraw,
        ConfigurationError,
    ) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _purchase_response(result)
