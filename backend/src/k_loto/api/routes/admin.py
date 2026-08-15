"""Authenticated Web Admin Panel API."""

import hmac
from datetime import datetime
from time import monotonic
from typing import Annotated, Any
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
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto import __version__
from k_loto.api.dependencies import get_db_session
from k_loto.application.admin import (
    AdminMutationService,
    AdminQueryService,
    ensure_admin_user,
)
from k_loto.core.config import Settings, get_settings
from k_loto.domain.enums import (
    AuditAction,
    DrawStatus,
    LedgerAccountKind,
    LotteryKind,
    TransactionType,
)
from k_loto.infrastructure.admin_auth import (
    ADMIN_COOKIE,
    AdminSession,
    InvalidAdminSession,
    issue_admin_session,
    validate_admin_session,
    verify_admin_password,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
started_at = monotonic()


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=512)


class SessionResponse(BaseModel):
    username: str
    csrf_token: str
    expires_at: datetime


class AdjustmentRequest(BaseModel):
    target_amount: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=512)
    idempotency_key: str = Field(min_length=1, max_length=100)


class AdjustmentResponse(BaseModel):
    amount: int
    already_processed: bool


class LotteryConfigurationRequest(BaseModel):
    ticket_price: int = Field(gt=0)
    base_jackpot: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=512)


class PlayerResponse(ApiModel):
    id: UUID
    display_name: str
    username: str | None
    telegram_id: int | None
    is_active: bool
    balance: int
    ticket_count: int
    spent: int
    won: int
    net: int


class LotteryResponse(ApiModel):
    id: UUID
    code: str
    name: str
    kind: LotteryKind
    ticket_price: int | None
    base_jackpot: int
    current_jackpot: int
    distribution_fund: int
    reserve: int
    schedule: dict[str, Any]
    sales_cutoff_minutes: int | None
    is_active: bool
    next_draw_number: int | None
    next_draw_at: datetime | None


class TransactionResponse(ApiModel):
    id: UUID
    operation_id: UUID
    type: TransactionType
    account_kind: LedgerAccountKind
    amount: int
    balance_before: int
    balance_after: int
    user_id: UUID | None
    lottery_id: UUID | None
    draw_id: UUID | None
    ticket_id: UUID | None
    created_at: datetime
    details: dict[str, Any]


class DrawResponse(ApiModel):
    id: UUID
    lottery_id: UUID
    lottery_code: str
    public_number: int
    status: DrawStatus
    scheduled_at: datetime
    sales_close_at: datetime
    executed_at: datetime | None
    winning_numbers: tuple[int, ...] | None
    ticket_count: int
    total_sales: int
    total_payout: int
    jackpot_opening: int | None
    jackpot_closing: int | None
    distribution_opening: int | None
    distribution_closing: int | None
    reserve_used: int
    correlation_id: UUID


class DrawTicketResponse(ApiModel):
    id: UUID
    public_number: int
    user_id: UUID
    numbers: tuple[int, ...]
    purchase_price: int
    matches: int | None
    prize_amount: int


class DrawDetailResponse(BaseModel):
    draw: DrawResponse
    tickets: list[DrawTicketResponse]


class NumberStatisticResponse(ApiModel):
    number: int
    appearances: int
    draw_percentage: float
    last_appearance: datetime | None
    draws_since_last: int | None


class AuditResponse(ApiModel):
    id: UUID
    admin_user_id: UUID
    action: AuditAction
    entity_type: str
    entity_id: UUID | None
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    reason: str | None
    created_at: datetime


class DashboardResponse(BaseModel):
    version: str
    uptime_seconds: int
    database_healthy: bool
    bot_configured: bool
    scheduler_enabled: bool
    counts: dict[str, int]
    lotteries: list[LotteryResponse]
    recent_draws: list[DrawResponse]
    recent_transactions: list[TransactionResponse]


class CurrentAdmin:
    def __init__(self, user_id: UUID, session: AdminSession) -> None:
        self.user_id = user_id
        self.session = session


def _validated_session(token: str | None, settings: Settings) -> AdminSession:
    if not settings.admin_auth_available or token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator authentication is required.",
        )
    secret = settings.admin_secret
    if secret is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        session = validate_admin_session(token, secret.get_secret_value())
    except InvalidAdminSession as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator session is invalid or expired.",
        ) from error
    expected_username = settings.admin_username or ""
    if not hmac.compare_digest(session.username, expected_username):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return session


async def get_current_admin(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    token: Annotated[str | None, Cookie(alias=ADMIN_COOKIE)] = None,
) -> CurrentAdmin:
    admin_session = _validated_session(token, settings)
    user_id = await ensure_admin_user(session, admin_session.username)
    return CurrentAdmin(user_id, admin_session)


async def require_admin_csrf(
    admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    csrf_token: Annotated[str | None, Header(alias="X-Admin-CSRF")] = None,
) -> CurrentAdmin:
    if csrf_token is None or not hmac.compare_digest(
        csrf_token, admin.session.csrf_token
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator CSRF token is missing or invalid.",
        )
    return admin


@router.post("/auth/login", response_model=SessionResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    if not settings.admin_auth_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Administrator authentication is not configured.",
        )
    configured_username = settings.admin_username or ""
    configured_hash = settings.admin_password_hash
    username_valid = hmac.compare_digest(payload.username, configured_username)
    password_valid = configured_hash is not None and verify_admin_password(
        payload.password, configured_hash.get_secret_value()
    )
    if not username_valid or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials.",
        )
    secret = settings.admin_secret
    if secret is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    token, admin_session = issue_admin_session(
        configured_username,
        secret.get_secret_value(),
        max_age_seconds=settings.admin_session_max_age_seconds,
    )
    response.set_cookie(
        key=ADMIN_COOKIE,
        value=token,
        max_age=settings.admin_session_max_age_seconds,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        path="/api/v1/admin",
    )
    return SessionResponse(
        username=admin_session.username,
        csrf_token=admin_session.csrf_token,
        expires_at=admin_session.expires_at,
    )


@router.get("/auth/session", response_model=SessionResponse)
async def current_session(
    admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> SessionResponse:
    return SessionResponse(
        username=admin.session.username,
        csrf_token=admin.session.csrf_token,
        expires_at=admin.session.expires_at,
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    _admin: Annotated[CurrentAdmin, Depends(require_admin_csrf)],
) -> None:
    response.delete_cookie(key=ADMIN_COOKIE, path="/api/v1/admin")


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DashboardResponse:
    service = AdminQueryService(session)
    lotteries = await service.lotteries()
    draws = await service.draws(limit=5)
    transactions = await service.transactions(limit=8)
    return DashboardResponse(
        version=__version__,
        uptime_seconds=int(monotonic() - started_at),
        database_healthy=True,
        bot_configured=settings.lottery_bot_token is not None,
        scheduler_enabled=settings.scheduler_enabled,
        counts=await service.dashboard_counts(),
        lotteries=[LotteryResponse.model_validate(item) for item in lotteries],
        recent_draws=[DrawResponse.model_validate(item) for item in draws],
        recent_transactions=[
            TransactionResponse.model_validate(item) for item in transactions
        ],
    )


@router.get("/players", response_model=list[PlayerResponse])
async def players(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[PlayerResponse]:
    return [
        PlayerResponse.model_validate(item)
        for item in await AdminQueryService(session).players()
    ]


@router.get("/players/{user_id}", response_model=PlayerResponse)
async def player(
    user_id: UUID,
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlayerResponse:
    try:
        item = await AdminQueryService(session).player(user_id)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return PlayerResponse.model_validate(item)


@router.post(
    "/players/{user_id}/balance-adjustments", response_model=AdjustmentResponse
)
async def adjust_player_balance(
    user_id: UUID,
    payload: AdjustmentRequest,
    admin: Annotated[CurrentAdmin, Depends(require_admin_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdjustmentResponse:
    try:
        result = await AdminMutationService(session, admin.user_id).set_user_balance(
            user_id,
            target_amount=payload.target_amount,
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return AdjustmentResponse(
        amount=result.amount, already_processed=result.already_processed
    )


@router.get("/lotteries", response_model=list[LotteryResponse])
async def lotteries(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[LotteryResponse]:
    return [
        LotteryResponse.model_validate(item)
        for item in await AdminQueryService(session).lotteries()
    ]


@router.put("/lotteries/{lottery_id}/configuration", response_model=LotteryResponse)
async def configure_lottery(
    lottery_id: UUID,
    payload: LotteryConfigurationRequest,
    admin: Annotated[CurrentAdmin, Depends(require_admin_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LotteryResponse:
    try:
        item = await AdminMutationService(session, admin.user_id).configure_lottery(
            lottery_id,
            ticket_price=payload.ticket_price,
            base_jackpot=payload.base_jackpot,
            reason=payload.reason,
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return LotteryResponse.model_validate(item)


@router.post(
    "/lotteries/{lottery_id}/reserve-adjustments",
    response_model=AdjustmentResponse,
)
async def adjust_reserve(
    lottery_id: UUID,
    payload: AdjustmentRequest,
    admin: Annotated[CurrentAdmin, Depends(require_admin_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdjustmentResponse:
    try:
        result = await AdminMutationService(session, admin.user_id).set_reserve(
            lottery_id,
            target_amount=payload.target_amount,
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return AdjustmentResponse(
        amount=result.amount, already_processed=result.already_processed
    )


@router.get("/transactions", response_model=list[TransactionResponse])
async def transactions(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    transaction_type: Annotated[TransactionType | None, Query(alias="type")] = None,
    user_id: UUID | None = None,
    lottery_id: UUID | None = None,
    draw_id: UUID | None = None,
    ticket_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[TransactionResponse]:
    if (date_from is not None and date_from.tzinfo is None) or (
        date_to is not None and date_to.tzinfo is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transaction date filters must include a timezone.",
        )
    items = await AdminQueryService(session).transactions(
        transaction_type=transaction_type,
        user_id=user_id,
        lottery_id=lottery_id,
        draw_id=draw_id,
        ticket_id=ticket_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return [TransactionResponse.model_validate(item) for item in items]


@router.get("/draws", response_model=list[DrawResponse])
async def draws(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    lottery_id: UUID | None = None,
    draw_status: Annotated[DrawStatus | None, Query(alias="status")] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[DrawResponse]:
    items = await AdminQueryService(session).draws(
        lottery_id=lottery_id, status=draw_status, limit=limit, offset=offset
    )
    return [DrawResponse.model_validate(item) for item in items]


@router.get("/draws/{draw_id}", response_model=DrawDetailResponse)
async def draw_detail(
    draw_id: UUID,
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DrawDetailResponse:
    try:
        draw, tickets = await AdminQueryService(session).draw(draw_id)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return DrawDetailResponse(
        draw=DrawResponse.model_validate(draw),
        tickets=[DrawTicketResponse.model_validate(item) for item in tickets],
    )


@router.get(
    "/lotteries/{lottery_id}/number-statistics",
    response_model=list[NumberStatisticResponse],
)
async def number_statistics(
    lottery_id: UUID,
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[NumberStatisticResponse]:
    try:
        items = await AdminQueryService(session).number_statistics(lottery_id)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return [NumberStatisticResponse.model_validate(item) for item in items]


@router.get("/audit", response_model=list[AuditResponse])
async def audit(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditResponse]:
    return [
        AuditResponse.model_validate(item)
        for item in await AdminQueryService(session).audit(limit=limit)
    ]
