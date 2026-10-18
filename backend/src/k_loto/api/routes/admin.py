"""Authenticated Web Admin Panel API."""

import hmac
from datetime import date, datetime
from time import monotonic
from typing import Annotated, Any, Literal
from uuid import UUID
from weakref import WeakKeyDictionary

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from k_loto import __version__
from k_loto.api.dependencies import get_db_session
from k_loto.application.admin import (
    AdminMutationService,
    AdminQueryService,
    ensure_admin_user,
)
from k_loto.application.display_cache import DisplayCache
from k_loto.application.economy import control_state
from k_loto.application.economy_archive import apply_archive_scope
from k_loto.application.economy_reporting import EconomyReportService
from k_loto.application.instant import InstantTicketQueryService
from k_loto.application.interesting_facts import InterestingFactAdminService
from k_loto.application.query_scope import LotteryScope
from k_loto.application.release_notes import ReleaseNoteKind, load_release_notes
from k_loto.application.runtime_monitoring import runtime_monitoring
from k_loto.core.config import Settings, get_settings
from k_loto.domain.enums import (
    AuditAction,
    DrawStatus,
    InterestingFactStatus,
    LedgerAccountKind,
    LotteryKind,
    NotificationStatus,
    NotificationType,
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
ticket_analytics_caches: WeakKeyDictionary[
    AsyncEngine, DisplayCache[tuple[Any, ...], "TicketAnalyticsResponse"]
] = WeakKeyDictionary()


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=512)
    remember_browser: bool = True


class SessionResponse(BaseModel):
    username: str
    csrf_token: str
    expires_at: datetime
    miniapp_url: str | None = None
    remembered: bool = False


class AdjustmentRequest(BaseModel):
    target_amount: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=512)
    idempotency_key: str = Field(min_length=1, max_length=100)


class AdjustmentResponse(BaseModel):
    amount: int
    already_processed: bool


class AutoPlayRequest(BaseModel):
    enabled: bool
    tickets_per_draw: int = Field(default=5, ge=1, le=5)
    reason: str = Field(min_length=1, max_length=512)


class LotteryConfigurationRequest(BaseModel):
    ticket_price: int = Field(gt=0)
    base_jackpot: int = Field(ge=0)
    sales_cutoff_minutes: int | None = Field(default=None, ge=0, le=1440)
    max_tickets_per_purchase: int | None = Field(default=None, ge=1, le=1000)
    max_tickets_per_user_per_draw: int | None = Field(default=None, ge=1, le=100_000)
    reason: str = Field(min_length=1, max_length=512)


class PlayerResponse(ApiModel):
    id: UUID
    display_name: str
    username: str | None
    telegram_id: int | None
    is_active: bool
    balance: int
    ticket_count: int
    active_ticket_count: int
    spent: int
    won: int
    net: int
    telegram_notifications_enabled: bool
    auto_play_enabled: bool
    auto_play_tickets_per_draw: int
    auto_play_last_attempted_at: datetime | None
    auto_play_last_succeeded_at: datetime | None
    auto_play_last_error: str | None


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
    max_tickets_per_purchase: int
    max_tickets_per_user_per_draw: int
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


class PlayerTicketHistoryItemResponse(ApiModel):
    id: UUID
    ticket_kind: str
    purchased_at: datetime
    lottery_id: UUID | None
    lottery_code: str
    lottery_name: str
    draw_number: int | None
    public_number: int
    numbers: tuple[int, ...]
    purchase_price: int
    prize_amount: int
    status: str
    source: str
    matches: int | None
    winning_numbers: tuple[int, ...] | None
    bingo_result: dict[str, Any] | None


class PlayerLotteryStatsResponse(ApiModel):
    lottery_id: UUID | None
    lottery_code: str
    lottery_name: str
    ticket_count: int
    active_ticket_count: int
    winning_ticket_count: int
    spent: int
    won: int


class PlayerHistoryResponse(BaseModel):
    items: list[PlayerTicketHistoryItemResponse]
    total: int
    offset: int
    limit: int
    lottery_stats: list[PlayerLotteryStatsResponse]


class DrawResponse(ApiModel):
    id: UUID
    lottery_id: UUID
    lottery_code: str
    lottery_name: str
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
    kasper_fund_used: int
    correlation_id: UUID
    jackpot_amount: int | None = None
    ruleset_code: str | None = None


class JackpotEventResponse(ApiModel):
    id: UUID
    lottery_code: str
    lottery_name: str
    draw_id: UUID
    draw_number: int
    jackpot_amount: int
    winner_ticket_count: int
    winner_user_count: int
    base_jackpot_after: int
    occurred_at: datetime


class ScheduleEntryResponse(ApiModel):
    id: UUID
    lottery_id: UUID
    lottery_name: str
    public_number: int
    scheduled_at: datetime


class DrawTicketResponse(ApiModel):
    id: UUID
    public_number: int
    user_id: UUID
    player_name: str
    player_username: str | None
    player_telegram_id: int | None
    is_jackpot_winner: bool
    numbers: tuple[int, ...]
    purchase_price: int
    matches: int | None
    prize_amount: int
    bingo_result: dict[str, Any] | None = None


class DrawDetailResponse(BaseModel):
    draw: DrawResponse
    tickets: list[DrawTicketResponse]
    ticket_summary: dict[str, Any] | None = None
    has_more: bool = False
    next_after: int | None = None


class NumberStatisticResponse(ApiModel):
    number: int
    appearances: int
    draw_percentage: float
    last_appearance: datetime | None
    draws_since_last: int | None


class NumberStatisticsReportResponse(ApiModel):
    lottery_id: UUID
    lottery_name: str
    period_start: datetime | None
    window_size: int | None
    draw_count: int
    first_draw_at: datetime | None
    last_draw_at: datetime | None
    numbers: list[NumberStatisticResponse]


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


class OverviewResponse(BaseModel):
    counts: dict[str, int]
    lotteries: list[LotteryResponse]
    recent_draws: list[DrawResponse]
    operations: dict[str, Any]
    jackpots: dict[str, Any]
    economy: dict[str, Any]


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
    operations: dict[str, Any]
    jackpots: dict[str, Any]


class KasperLiveSummaryResponse(BaseModel):
    ticket_count: int
    winning_tickets: int
    losing_tickets: int
    result: int


class ReleaseNoteResponse(BaseModel):
    version: str
    date: str | None
    content: str
    sequence: int | None = None


class TicketAnalyticsRowResponse(ApiModel):
    lottery_id: UUID | None
    lottery_name: str
    is_active: bool | None
    total_tickets: int
    active_tickets: int
    settled_tickets: int
    winning_tickets: int
    participants: int
    winning_players: int
    total_sales: int
    total_payout: int


class TicketAnalyticsResponse(ApiModel):
    overall: TicketAnalyticsRowResponse
    lotteries: list[TicketAnalyticsRowResponse]


class ActivityPointResponse(ApiModel):
    bucket_at: datetime
    ticket_count: int
    total_sales: int
    total_payout: int


class NotificationResponse(ApiModel):
    id: UUID
    event_key: str
    user_id: UUID
    type: NotificationType
    status: NotificationStatus
    attempts: int
    available_at: datetime
    sent_at: datetime | None
    last_error: str | None
    payload: dict[str, Any]
    created_at: datetime


class InterestingFactResponse(ApiModel):
    id: UUID
    generation_date: date
    generated_at: datetime
    lottery_id: UUID
    lottery_code: str
    lottery_name: str
    fact_type: str
    title: str
    description: str
    numeric_values: dict[str, Any]
    score: int
    status: InterestingFactStatus


class InterestingFactStatusRequest(BaseModel):
    status: InterestingFactStatus


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
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    token: Annotated[str | None, Cookie(alias=ADMIN_COOKIE)] = None,
) -> CurrentAdmin:
    admin_session = _validated_session(token, settings)
    user_id = await ensure_admin_user(session, admin_session.username)
    if request.method == "GET":
        control = await control_state(session)
        epoch, started = control.epoch, control.epoch_started_at
        # Authentication already committed its identity; leave the read handler
        # free to use its own transaction while filtering every Admin route.
        await session.rollback()
        apply_archive_scope(
            session,
            epoch=epoch,
            started_at=started,
            archive=request.headers.get("X-Economy-Scope") == "archive",
        )
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


@router.get("/monitoring")
async def operational_snapshot(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> dict[str, Any]:
    return runtime_monitoring.snapshot()


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
    max_age = (
        settings.admin_remember_max_age_seconds
        if payload.remember_browser
        else settings.admin_session_max_age_seconds
    )
    token, admin_session = issue_admin_session(
        configured_username,
        secret.get_secret_value(),
        max_age_seconds=max_age,
        remembered=payload.remember_browser,
    )
    response.set_cookie(
        key=ADMIN_COOKIE,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        path="/api/v1/admin",
    )
    return SessionResponse(
        username=admin_session.username,
        csrf_token=admin_session.csrf_token,
        expires_at=admin_session.expires_at,
        miniapp_url=str(settings.miniapp_url) if settings.miniapp_url else None,
        remembered=admin_session.remembered,
    )


@router.get("/auth/session", response_model=SessionResponse)
async def current_session(
    response: Response,
    admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    current = admin.session
    if current.remembered:
        secret = settings.admin_secret
        if secret is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        token, current = issue_admin_session(
            current.username,
            secret.get_secret_value(),
            max_age_seconds=settings.admin_remember_max_age_seconds,
            remembered=True,
        )
        response.set_cookie(
            key=ADMIN_COOKIE,
            value=token,
            max_age=settings.admin_remember_max_age_seconds,
            httponly=True,
            secure=settings.app_env == "production",
            samesite="strict",
            path="/api/v1/admin",
        )
    return SessionResponse(
        username=current.username,
        csrf_token=current.csrf_token,
        expires_at=current.expires_at,
        miniapp_url=str(settings.miniapp_url) if settings.miniapp_url else None,
        remembered=current.remembered,
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    _admin: Annotated[CurrentAdmin, Depends(require_admin_csrf)],
) -> None:
    response.delete_cookie(key=ADMIN_COOKIE, path="/api/v1/admin")


@router.get("/economy")
async def economy_report(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = Query(default=7, ge=7, le=30),
    through: date | None = None,
) -> dict[str, Any]:
    try:
        return await EconomyReportService(session).daily(days=days, through=through)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/overview", response_model=OverviewResponse)
async def overview(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    scope: LotteryScope = "all",
) -> OverviewResponse:
    """Business-only projection: diagnostics and journals load in System."""
    service = AdminQueryService(session, scope=scope)
    control = await control_state(session)
    return OverviewResponse(
        counts=await service.dashboard_counts(),
        recent_draws=[
            DrawResponse.model_validate(x) for x in await service.draws(limit=5)
        ],
        lotteries=[
            LotteryResponse.model_validate(x) for x in await service.lotteries()
        ],
        operations=await service.operational_status(technical=False),
        jackpots=await service.jackpot_analytics(),
        economy={
            "epoch": control.epoch,
            "started_at": control.epoch_started_at,
            "paused": control.paused,
            "scope": session.info.get("economy_scope", (1, "current"))[1],
        },
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    scope: LotteryScope = "all",
) -> DashboardResponse:
    service = AdminQueryService(session, scope=scope)
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
        operations=await service.operational_status(),
        jackpots=await service.jackpot_analytics(),
    )


@router.get("/kasper-live", response_model=KasperLiveSummaryResponse)
async def kasper_live_summary(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KasperLiveSummaryResponse:
    item = await InstantTicketQueryService(session).summary()
    return KasperLiveSummaryResponse(
        ticket_count=item.ticket_count,
        winning_tickets=item.winning_tickets,
        losing_tickets=item.losing_tickets,
        result=item.result,
    )


@router.get("/aurora", response_model=KasperLiveSummaryResponse)
async def aurora_summary(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KasperLiveSummaryResponse:
    item = await InstantTicketQueryService(session).summary("aurora")
    return KasperLiveSummaryResponse(
        ticket_count=item.ticket_count,
        winning_tickets=item.winning_tickets,
        losing_tickets=item.losing_tickets,
        result=item.result,
    )


@router.get("/vault", response_model=KasperLiveSummaryResponse)
async def vault_summary(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KasperLiveSummaryResponse:
    item = await InstantTicketQueryService(session).summary("vault")
    return KasperLiveSummaryResponse(
        ticket_count=item.ticket_count,
        winning_tickets=item.winning_tickets,
        losing_tickets=item.losing_tickets,
        result=item.result,
    )


@router.get("/notifications", response_model=list[NotificationResponse])
async def notifications(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    notification_status: Annotated[NotificationStatus | None, Query()] = None,
    user_id: Annotated[UUID | None, Query()] = None,
) -> list[NotificationResponse]:
    items = await AdminQueryService(session).notifications(
        status=notification_status, user_id=user_id
    )
    return [NotificationResponse.model_validate(item) for item in items]


@router.get("/players", response_model=list[PlayerResponse])
async def players(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[str | None, Query(alias="q", max_length=128)] = None,
    limit: int = Query(default=200, ge=1, le=500),
) -> list[PlayerResponse]:
    return [
        PlayerResponse.model_validate(item)
        for item in await AdminQueryService(session).players(search=query, limit=limit)
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


@router.get("/players/{user_id}/ticket-history", response_model=PlayerHistoryResponse)
async def player_ticket_history(
    user_id: UUID,
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    history_filter: Annotated[
        Literal["all", "purchases", "wins"], Query(alias="filter")
    ] = "all",
    lottery_code: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PlayerHistoryResponse:
    try:
        items, total, stats = await AdminQueryService(session).player_ticket_history(
            user_id,
            history_filter=history_filter,
            lottery_code=lottery_code,
            limit=limit,
            offset=offset,
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return PlayerHistoryResponse(
        items=[PlayerTicketHistoryItemResponse.model_validate(item) for item in items],
        total=total,
        offset=offset,
        limit=limit,
        lottery_stats=[
            PlayerLotteryStatsResponse.model_validate(item) for item in stats
        ],
    )


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


@router.put("/players/{user_id}/auto-play", response_model=PlayerResponse)
async def configure_player_auto_play(
    user_id: UUID,
    payload: AutoPlayRequest,
    admin: Annotated[CurrentAdmin, Depends(require_admin_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlayerResponse:
    try:
        await AdminMutationService(session, admin.user_id).set_auto_play(
            user_id,
            enabled=payload.enabled,
            tickets_per_draw=payload.tickets_per_draw,
            reason=payload.reason,
        )
        item = await AdminQueryService(session).player(user_id)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return PlayerResponse.model_validate(item)


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
            sales_cutoff_minutes=payload.sales_cutoff_minutes,
            max_tickets_per_purchase=payload.max_tickets_per_purchase,
            max_tickets_per_user_per_draw=payload.max_tickets_per_user_per_draw,
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
    "/lotteries/{lottery_id}/jackpot-adjustments",
    response_model=AdjustmentResponse,
)
async def adjust_jackpot(
    lottery_id: UUID,
    payload: AdjustmentRequest,
    admin: Annotated[CurrentAdmin, Depends(require_admin_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdjustmentResponse:
    try:
        result = await AdminMutationService(session, admin.user_id).set_jackpot(
            lottery_id,
            target_amount=payload.target_amount,
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return AdjustmentResponse(
        amount=result.amount, already_processed=result.already_processed
    )


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
    before_at: datetime | None = None,
    before_id: UUID | None = None,
) -> list[TransactionResponse]:
    if (date_from is not None and date_from.tzinfo is None) or (
        date_to is not None and date_to.tzinfo is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transaction date filters must include a timezone.",
        )
    if (before_at is None) != (before_id is None) or (
        before_at is not None and (before_at.tzinfo is None or offset != 0)
    ):
        raise HTTPException(status_code=422, detail="Invalid transaction cursor.")
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
        before_at=before_at,
        before_id=before_id,
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
    scope: LotteryScope = "all",
    period: Literal["today", "future", "completed", "failed", "archived"] | None = None,
) -> list[DrawResponse]:
    items = await AdminQueryService(session, scope=scope).draws(
        lottery_id=lottery_id,
        status=draw_status,
        limit=limit,
        offset=offset,
        period=period,
    )
    return [DrawResponse.model_validate(item) for item in items]


@router.get("/jackpots", response_model=list[JackpotEventResponse])
async def jackpot_events(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    lottery_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    scope: LotteryScope = "all",
) -> list[JackpotEventResponse]:
    items = await AdminQueryService(session, scope=scope).jackpot_events(
        lottery_id=lottery_id, limit=limit, offset=offset
    )
    return [JackpotEventResponse.model_validate(item) for item in items]


@router.get("/schedule", response_model=list[ScheduleEntryResponse])
async def daily_schedule(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    lottery_id: UUID | None = None,
    scope: LotteryScope = "all",
) -> list[ScheduleEntryResponse]:
    items = await AdminQueryService(session, scope=scope).daily_schedule(
        lottery_id=lottery_id
    )
    return [ScheduleEntryResponse.model_validate(item) for item in items]


@router.get("/draws/{draw_id}", response_model=DrawDetailResponse)
async def draw_detail(
    draw_id: UUID,
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=0, le=100)] = 50,
    after: Annotated[int, Query(ge=0)] = 0,
    ticket_filter: Literal["all", "winners", "jackpot"] = "all",
    include_summary: bool = True,
) -> DrawDetailResponse:
    service = AdminQueryService(session)
    try:
        draw, tickets = await service.draw(
            draw_id,
            limit=limit + 1 if limit else 0,
            after=after,
            ticket_filter=ticket_filter,
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    summary = (
        await service.draw_ticket_summary(draw_id, draw.lottery_code, draw.ruleset_code)
        if include_summary
        else None
    )
    page = tickets[:limit]
    return DrawDetailResponse(
        draw=DrawResponse.model_validate(draw),
        tickets=[DrawTicketResponse.model_validate(item) for item in page],
        ticket_summary=summary,
        has_more=len(tickets) > limit,
        next_after=page[-1].public_number if len(tickets) > limit else None,
    )


@router.get(
    "/lotteries/{lottery_id}/number-statistics",
    response_model=NumberStatisticsReportResponse,
)
async def number_statistics(
    lottery_id: UUID,
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    date_from: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=0, le=100)] = 20,
) -> NumberStatisticsReportResponse:
    try:
        report = await AdminQueryService(session).number_statistics(
            lottery_id,
            date_from=date_from,
            limit=limit or None,
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return NumberStatisticsReportResponse.model_validate(report)


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


@router.get("/interesting-facts", response_model=list[InterestingFactResponse])
async def interesting_facts(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    fact_status: Annotated[InterestingFactStatus | None, Query()] = None,
    lottery_id: Annotated[UUID | None, Query()] = None,
    fact_type: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
) -> list[InterestingFactResponse]:
    items = await InterestingFactAdminService(session).list(
        status=fact_status,
        lottery_id=lottery_id,
        fact_type=fact_type,
        limit=limit,
    )
    return [InterestingFactResponse.model_validate(item) for item in items]


@router.patch(
    "/interesting-facts/{fact_id}/status",
    response_model=InterestingFactResponse,
)
async def update_interesting_fact_status(
    fact_id: UUID,
    payload: InterestingFactStatusRequest,
    _admin: Annotated[CurrentAdmin, Depends(require_admin_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InterestingFactResponse:
    async with session.begin():
        item = await InterestingFactAdminService(session).set_status(
            fact_id, payload.status
        )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return InterestingFactResponse.model_validate(item)


@router.get("/ticket-analytics", response_model=TicketAnalyticsResponse)
async def ticket_analytics(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    scope: LotteryScope = "all",
) -> TicketAnalyticsResponse:
    """Single-flight display analytics for every scope; no personal cache values."""

    async def load() -> TicketAnalyticsResponse:
        return TicketAnalyticsResponse.model_validate(
            await AdminQueryService(session, scope=scope).ticket_analytics()
        )

    if not isinstance(session.bind, AsyncEngine):
        return await load()
    cache = ticket_analytics_caches.setdefault(session.bind, DisplayCache(seconds=60))
    return await cache.get((scope, session.info.get("economy_scope")), load)


@router.get("/activity", response_model=list[ActivityPointResponse])
async def activity(
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period_days: int = Query(default=1, ge=1, le=30),
    scope: LotteryScope = "all",
) -> list[ActivityPointResponse]:
    """Return lightweight sales and payout buckets when the dashboard is opened."""

    rows = await AdminQueryService(session, scope=scope).activity(
        period_days=period_days
    )
    return [ActivityPointResponse.model_validate(item) for item in rows]


@router.get("/release-notes/{kind}", response_model=list[ReleaseNoteResponse])
async def release_notes(
    kind: ReleaseNoteKind,
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> list[ReleaseNoteResponse]:
    """Return the complete versioned project history to an authenticated admin."""

    return [
        ReleaseNoteResponse.model_validate(item, from_attributes=True)
        for item in load_release_notes(kind)
    ]


@router.get("/distribution-draws")
async def distribution_draws(
    lottery_id: UUID,
    day: date,
    _admin: Annotated[CurrentAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    from k_loto.application.distribution import DistributionDrawService

    return await DistributionDrawService(session).list(lottery_id, day)


class DistributionDrawInput(BaseModel):
    lottery_id: UUID
    scheduled_at: datetime


@router.post("/distribution-draws/{draw_id}")
async def assign_distribution_draw(
    draw_id: UUID,
    payload: DistributionDrawInput,
    background: BackgroundTasks,
    admin: Annotated[CurrentAdmin, Depends(require_admin_csrf)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    from k_loto.application.distribution import (
        DistributionDrawService,
        drain_distribution,
        projected_id,
    )
    from k_loto.infrastructure.database.session import session_factory

    try:
        service = DistributionDrawService(session)
        if payload.scheduled_at.tzinfo is None:
            raise ValueError("Дата должна содержать часовой пояс.")
        if draw_id == projected_id(payload.lottery_id, payload.scheduled_at):
            draw_id = await service.prepare(
                payload.lottery_id, payload.scheduled_at, draw_id
            )
        result = await service.assign(draw_id, admin.user_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    background.add_task(drain_distribution, session_factory)
    return result
