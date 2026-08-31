"""Authenticated Telegram Mini App API."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.api.dependencies import (
    CurrentMiniAppUser,
    get_current_miniapp_user,
    get_db_session,
)
from k_loto.application.daily import DailyTicketPurchaseService
from k_loto.application.dev_mode import DevBootstrapConfig, DevBootstrapService
from k_loto.application.miniapp import (
    MiniAppDashboard,
    MiniAppLiveDraw,
    MiniAppLiveFeed,
    MiniAppLottery,
    MiniAppQueryService,
    MiniAppTicket,
)
from k_loto.application.weekly import (
    MAX_TICKETS_PER_PURCHASE,
    WeeklyTicketPurchaseService,
)
from k_loto.core.config import Settings, get_settings
from k_loto.domain.enums import LotteryKind, TicketStatus
from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InvalidTicket,
    NoAvailableDraw,
)
from k_loto.domain.lotteries import DAILY_LOTTERY_CODES, PLAYABLE_LOTTERY_CODES
from k_loto.infrastructure.local_dev_auth import (
    LOCAL_DEV_COOKIE,
    is_loopback_authority,
    is_loopback_host,
    is_loopback_origin,
    issue_local_dev_session,
)

router = APIRouter(prefix="/api/v1/miniapp", tags=["miniapp"])


class LotteryResponse(BaseModel):
    code: str
    name: str
    kind: LotteryKind
    numbers_to_pick: int
    max_number: int
    ticket_price: int | None
    jackpot: int
    draw_number: int | None
    scheduled_at: datetime | None
    sales_close_at: datetime | None
    sales_open: bool
    purchase_available: bool
    player_ticket_count: int


class TicketResponse(BaseModel):
    id: UUID
    public_number: int
    lottery_code: str
    lottery_name: str
    draw_number: int
    scheduled_at: datetime
    numbers: list[int]
    purchase_price: int
    status: TicketStatus
    matches: int | None
    prize_amount: int
    winning_numbers: list[int] | None


class DashboardResponse(BaseModel):
    server_time: datetime
    balance: int
    active_ticket_count: int
    lotteries: list[LotteryResponse]
    recent_results: list[TicketResponse]


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]


class LiveTicketResponse(BaseModel):
    public_number: int
    numbers: list[int]
    matches: int | None
    prize_amount: int


class LiveDrawResponse(BaseModel):
    lottery_code: str
    lottery_name: str
    lottery_kind: LotteryKind
    draw_number: int
    scheduled_at: datetime
    status: str
    winning_numbers: list[int] | None
    jackpot: int
    player_ticket_count: int
    player_winning_ticket_count: int
    player_best_matches: int | None
    player_total_prize: int
    highlighted_tickets: list[LiveTicketResponse]


class LiveFeedResponse(BaseModel):
    server_time: datetime
    latest_completed: LiveDrawResponse | None
    next_scheduled: LiveDrawResponse | None


class PurchaseRequest(BaseModel):
    combinations: list[list[int]] = Field(
        min_length=1, max_length=MAX_TICKETS_PER_PURCHASE
    )
    idempotency_key: str = Field(min_length=1, max_length=100)


class PurchaseResponse(BaseModel):
    operation_id: UUID
    draw_id: UUID
    ticket_ids: list[UUID]
    total_cost: int
    balance_after: int
    already_processed: bool


class DevSessionResponse(BaseModel):
    mode: Literal["local-development"]


class DevRefillResponse(BaseModel):
    balance: int


@router.post("/dev/session", response_model=DevSessionResponse)
async def create_local_dev_session(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> DevSessionResponse:
    """Issue a loopback-only HttpOnly session; unavailable outside development."""
    if not settings.local_dev_auth_available:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    client_host = request.client.host if request.client else None
    if (
        not is_loopback_host(client_host)
        or not is_loopback_authority(request.headers.get("host"))
        or not is_loopback_origin(request.headers.get("origin"))
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local development sessions require a loopback browser.",
        )
    secret = settings.miniapp_dev_session_secret
    if secret is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    token = issue_local_dev_session(
        secret.get_secret_value(),
        max_age_seconds=settings.miniapp_dev_session_max_age_seconds,
    )
    response.set_cookie(
        key=LOCAL_DEV_COOKIE,
        value=token,
        max_age=settings.miniapp_dev_session_max_age_seconds,
        httponly=True,
        secure=False,
        samesite="strict",
        path="/api/v1/miniapp",
    )
    return DevSessionResponse(mode="local-development")


@router.post("/dev/refill", response_model=DevRefillResponse)
async def refill_local_dev_balance(
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DevRefillResponse:
    if not settings.local_dev_auth_available:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    balance = await DevBootstrapService(
        session,
        DevBootstrapConfig(
            initial_user_balance=settings.miniapp_dev_initial_balance,
            weekly_ticket_price=settings.miniapp_dev_weekly_ticket_price,
            weekly_base_jackpot=settings.miniapp_dev_weekly_base_jackpot,
            weekly_reserve=settings.miniapp_dev_weekly_reserve,
        ),
    ).refill_user(user.id, settings.miniapp_dev_initial_balance)
    return DevRefillResponse(balance=balance)


def _lottery_response(item: MiniAppLottery) -> LotteryResponse:
    return LotteryResponse(
        code=item.code,
        name=item.name,
        kind=item.kind,
        numbers_to_pick=item.numbers_to_pick,
        max_number=item.max_number,
        ticket_price=item.ticket_price,
        jackpot=item.jackpot,
        draw_number=item.draw_number,
        scheduled_at=item.scheduled_at,
        sales_close_at=item.sales_close_at,
        sales_open=item.sales_open,
        purchase_available=item.purchase_available,
        player_ticket_count=item.player_ticket_count,
    )


def _ticket_response(item: MiniAppTicket) -> TicketResponse:
    return TicketResponse(
        id=item.id,
        public_number=item.public_number,
        lottery_code=item.lottery_code,
        lottery_name=item.lottery_name,
        draw_number=item.draw_number,
        scheduled_at=item.scheduled_at,
        numbers=list(item.numbers),
        purchase_price=item.purchase_price,
        status=item.status,
        matches=item.matches,
        prize_amount=item.prize_amount,
        winning_numbers=(list(item.winning_numbers) if item.winning_numbers else None),
    )


def _dashboard_response(item: MiniAppDashboard) -> DashboardResponse:
    return DashboardResponse(
        server_time=item.server_time,
        balance=item.balance,
        active_ticket_count=item.active_ticket_count,
        lotteries=[_lottery_response(value) for value in item.lotteries],
        recent_results=[_ticket_response(value) for value in item.recent_results],
    )


def _live_draw_response(item: MiniAppLiveDraw) -> LiveDrawResponse:
    return LiveDrawResponse(
        lottery_code=item.lottery_code,
        lottery_name=item.lottery_name,
        lottery_kind=item.lottery_kind,
        draw_number=item.draw_number,
        scheduled_at=item.scheduled_at,
        status=item.status.value,
        winning_numbers=(list(item.winning_numbers) if item.winning_numbers else None),
        jackpot=item.jackpot,
        player_ticket_count=item.player_ticket_count,
        player_winning_ticket_count=item.player_winning_ticket_count,
        player_best_matches=item.player_best_matches,
        player_total_prize=item.player_total_prize,
        highlighted_tickets=[
            LiveTicketResponse(
                public_number=ticket.public_number,
                numbers=list(ticket.numbers),
                matches=ticket.matches,
                prize_amount=ticket.prize_amount,
            )
            for ticket in item.highlighted_tickets
        ],
    )


def _live_response(item: MiniAppLiveFeed) -> LiveFeedResponse:
    return LiveFeedResponse(
        server_time=item.server_time,
        latest_completed=(
            _live_draw_response(item.latest_completed)
            if item.latest_completed
            else None
        ),
        next_scheduled=(
            _live_draw_response(item.next_scheduled) if item.next_scheduled else None
        ),
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardResponse:
    return _dashboard_response(await MiniAppQueryService(session).dashboard(user.id))


@router.get("/live", response_model=LiveFeedResponse)
async def live(
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LiveFeedResponse:
    return _live_response(await MiniAppQueryService(session).live(user.id))


@router.get("/tickets", response_model=TicketListResponse)
async def tickets(
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    state: Annotated[Literal["active", "history"], Query()] = "active",
) -> TicketListResponse:
    items = await MiniAppQueryService(session).tickets(
        user.id, active=state == "active"
    )
    return TicketListResponse(tickets=[_ticket_response(item) for item in items])


@router.post(
    "/weekly/purchases",
    response_model=PurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def purchase_weekly_tickets(
    request: PurchaseRequest,
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PurchaseResponse:
    try:
        result = await WeeklyTicketPurchaseService(session).purchase(
            user_id=user.id,
            combinations=[list(combination) for combination in request.combinations],
            idempotency_key=request.idempotency_key,
        )
    except InsufficientBalance as error:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient CAS balance.",
        ) from error
    except InvalidTicket as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except NoAvailableDraw as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No Weekly draw is currently open for sales.",
        ) from error
    except ConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weekly lottery is not configured.",
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
async def purchase_daily_tickets(
    request: PurchaseRequest,
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PurchaseResponse:
    try:
        result = await DailyTicketPurchaseService(session).purchase(
            user_id=user.id,
            combinations=[list(value) for value in request.combinations],
            idempotency_key=request.idempotency_key,
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


@router.post(
    "/lotteries/{lottery_code}/purchases",
    response_model=PurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def purchase_lottery_tickets(
    lottery_code: str,
    request: PurchaseRequest,
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PurchaseResponse:
    if lottery_code not in PLAYABLE_LOTTERY_CODES:
        raise HTTPException(status_code=404, detail="Lottery is not available.")
    service = (
        DailyTicketPurchaseService(session, lottery_code=lottery_code)
        if lottery_code in DAILY_LOTTERY_CODES
        else WeeklyTicketPurchaseService(session, lottery_code=lottery_code)
    )
    try:
        result = await service.purchase(
            user_id=user.id,
            combinations=[list(value) for value in request.combinations],
            idempotency_key=request.idempotency_key,
        )
    except InsufficientBalance as error:
        raise HTTPException(
            status_code=402, detail="Insufficient CAS balance."
        ) from error
    except InvalidTicket as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except NoAvailableDraw as error:
        raise HTTPException(
            status_code=409, detail="No draw is open for sales."
        ) from error
    except ConfigurationError as error:
        raise HTTPException(
            status_code=503, detail="Lottery is not configured."
        ) from error
    return PurchaseResponse(
        operation_id=result.operation_id,
        draw_id=result.draw_id,
        ticket_ids=list(result.ticket_ids),
        total_cost=result.total_cost,
        balance_after=result.balance_after,
        already_processed=result.already_processed,
    )
