"""Authenticated Telegram Mini App API."""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.api.dependencies import (
    CurrentMiniAppUser,
    get_current_miniapp_user,
    get_db_session,
)
from k_loto.application.daily import DailyTicketPurchaseService
from k_loto.application.dev_mode import DevBootstrapConfig, DevBootstrapService
from k_loto.application.favorites import FavoriteCombinationService
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
from k_loto.domain.enums import (
    InAppNotificationType,
    LotteryKind,
    TicketSource,
    TicketStatus,
)
from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InvalidTicket,
    NoAvailableDraw,
)
from k_loto.domain.lotteries import DAILY_LOTTERY_CODES, PLAYABLE_LOTTERY_CODES
from k_loto.infrastructure.database.models import Lottery
from k_loto.infrastructure.database.session import session_factory
from k_loto.infrastructure.local_dev_auth import (
    LOCAL_DEV_COOKIE,
    is_loopback_authority,
    is_loopback_host,
    is_loopback_origin,
    issue_local_dev_session,
)
from k_loto.infrastructure.rate_limit import purchase_rate_limiter

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
    sales_status: str
    max_tickets_per_purchase: int
    max_tickets_per_user_per_draw: int


class TicketResponse(BaseModel):
    id: UUID
    public_number: int
    lottery_code: str
    lottery_name: str
    draw_number: int
    scheduled_at: datetime
    numbers: list[int]
    purchase_price: int
    source: TicketSource
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
    monthly_total_payout: int


class NotificationPreferencesResponse(BaseModel):
    telegram_enabled: bool
    draw_results_enabled: bool
    inactivity_reminders_enabled: bool


class NotificationPreferencesRequest(NotificationPreferencesResponse):
    pass


class AccountResponse(BaseModel):
    display_name: str
    balance: int
    ticket_count: int
    active_ticket_count: int
    winning_ticket_count: int
    total_spent: int
    total_won: int
    best_win: int
    unread_notification_count: int
    notification_preferences: NotificationPreferencesResponse


class UserNotificationResponse(BaseModel):
    id: UUID
    type: InAppNotificationType
    title: str
    body: str
    payload: dict[str, object]
    read_at: datetime | None
    created_at: datetime


class ReadNotificationsRequest(BaseModel):
    notification_id: UUID | None = None


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]


class FavoriteRequest(BaseModel):
    numbers: list[int]


class FavoriteResponse(BaseModel):
    id: UUID
    numbers: list[int]


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
    sales_close_at: datetime
    sales_status: str
    live_starts_at: datetime
    reveal_at: list[datetime]
    live_ends_at: datetime


class LiveFeedResponse(BaseModel):
    server_time: datetime
    latest_completed: LiveDrawResponse | None
    next_scheduled: LiveDrawResponse | None
    recent_completed: list[LiveDrawResponse]


class PurchaseRequest(BaseModel):
    combinations: list[list[int]] = Field(
        min_length=1, max_length=MAX_TICKETS_PER_PURCHASE
    )
    idempotency_key: str = Field(min_length=1, max_length=100)
    draw_count: Literal[1, 5] = 1


class PurchaseResponse(BaseModel):
    operation_id: UUID
    draw_id: UUID
    draw_ids: list[UUID]
    draw_count: int
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
        sales_status=item.sales_status,
        max_tickets_per_purchase=item.max_tickets_per_purchase,
        max_tickets_per_user_per_draw=item.max_tickets_per_user_per_draw,
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
        source=item.source,
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
        monthly_total_payout=item.monthly_total_payout,
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
        sales_close_at=item.sales_close_at,
        sales_status=item.sales_status,
        live_starts_at=item.live_starts_at,
        reveal_at=list(item.reveal_at),
        live_ends_at=item.live_ends_at,
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
        recent_completed=[_live_draw_response(draw) for draw in item.recent_completed],
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardResponse:
    return _dashboard_response(await MiniAppQueryService(session).dashboard(user.id))


@router.get("/account", response_model=AccountResponse)
async def account(
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountResponse:
    item = await MiniAppQueryService(session).account(user.id)
    return AccountResponse(
        display_name=item.display_name,
        balance=item.balance,
        ticket_count=item.ticket_count,
        active_ticket_count=item.active_ticket_count,
        winning_ticket_count=item.winning_ticket_count,
        total_spent=item.total_spent,
        total_won=item.total_won,
        best_win=item.best_win,
        unread_notification_count=item.unread_notification_count,
        notification_preferences=NotificationPreferencesResponse(
            telegram_enabled=item.notification_preferences.telegram_enabled,
            draw_results_enabled=item.notification_preferences.draw_results_enabled,
            inactivity_reminders_enabled=(
                item.notification_preferences.inactivity_reminders_enabled
            ),
        ),
    )


@router.get("/notifications", response_model=list[UserNotificationResponse])
async def user_notifications(
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[UserNotificationResponse]:
    return [
        UserNotificationResponse(
            id=item.id,
            type=item.type,
            title=item.title,
            body=item.body,
            payload=item.payload,
            read_at=item.read_at,
            created_at=item.created_at,
        )
        for item in await MiniAppQueryService(session).notifications(user.id)
    ]


@router.put("/notification-preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    payload: NotificationPreferencesRequest,
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationPreferencesResponse:
    item = await MiniAppQueryService(session).set_notification_preferences(
        user.id,
        telegram_enabled=payload.telegram_enabled,
        draw_results_enabled=payload.draw_results_enabled,
        inactivity_reminders_enabled=payload.inactivity_reminders_enabled,
    )
    return NotificationPreferencesResponse(
        telegram_enabled=item.telegram_enabled,
        draw_results_enabled=item.draw_results_enabled,
        inactivity_reminders_enabled=item.inactivity_reminders_enabled,
    )


@router.post("/notifications/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_user_notifications_read(
    payload: ReadNotificationsRequest,
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    await MiniAppQueryService(session).mark_notifications_read(
        user.id, payload.notification_id
    )


@router.post("/notifications/test", status_code=status.HTTP_202_ACCEPTED)
async def test_telegram_delivery(
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, bool]:
    """Queue a user-requested end-to-end Telegram delivery check."""

    try:
        queued = await MiniAppQueryService(session).queue_delivery_test(user.id)
    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(error)
        ) from error
    return {"queued": queued}


@router.get("/live", response_model=LiveFeedResponse)
async def live(
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LiveFeedResponse:
    return _live_response(await MiniAppQueryService(session).live(user.id))


@router.get("/live/stream")
async def live_stream(
    request: Request,
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
) -> StreamingResponse:
    """Push the authoritative live snapshot; fetch streaming keeps auth in headers."""

    async def events() -> AsyncIterator[str]:
        previous = ""
        while not await request.is_disconnected():
            async with session_factory() as session:
                payload = _live_response(
                    await MiniAppQueryService(session).live(user.id)
                ).model_dump_json()
            if payload != previous:
                yield f"event: snapshot\ndata: {payload}\n\n"
                previous = payload
            else:
                yield ": keep-alive\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tickets", response_model=TicketListResponse)
async def tickets(
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    state: Annotated[Literal["active", "history"], Query()] = "active",
    lottery_code: Annotated[str | None, Query(max_length=32)] = None,
    wins_only: Annotated[bool, Query()] = False,
) -> TicketListResponse:
    items = await MiniAppQueryService(session).tickets(
        user.id,
        active=state == "active",
        lottery_code=lottery_code,
        wins_only=wins_only,
    )
    return TicketListResponse(tickets=[_ticket_response(item) for item in items])


async def _favorite_lottery(session: AsyncSession, lottery_code: str) -> UUID:
    lottery_id = await session.scalar(
        select(Lottery.id).where(
            Lottery.code == lottery_code,
            Lottery.is_active.is_(True),
        )
    )
    if lottery_id is None:
        raise HTTPException(status_code=404, detail="Lottery is not available.")
    return lottery_id


@router.get(
    "/lotteries/{lottery_code}/favorites", response_model=list[FavoriteResponse]
)
async def favorites(
    lottery_code: str,
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[FavoriteResponse]:
    lottery_id = await _favorite_lottery(session, lottery_code)
    items = await FavoriteCombinationService(session).list_for_lottery(
        user_id=user.id, lottery_id=lottery_id
    )
    return [FavoriteResponse(id=item.id, numbers=list(item.numbers)) for item in items]


@router.post(
    "/lotteries/{lottery_code}/favorites",
    response_model=FavoriteResponse,
    status_code=201,
)
async def save_favorite(
    lottery_code: str,
    request: FavoriteRequest,
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FavoriteResponse:
    lottery_id = await _favorite_lottery(session, lottery_code)
    try:
        item, _ = await FavoriteCombinationService(session).save(
            user_id=user.id,
            lottery_id=lottery_id,
            numbers=tuple(request.numbers),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return FavoriteResponse(id=item.id, numbers=list(item.numbers))


@router.delete("/lotteries/{lottery_code}/favorites/{favorite_id}", status_code=204)
async def delete_favorite(
    lottery_code: str,
    favorite_id: UUID,
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    lottery_id = await _favorite_lottery(session, lottery_code)
    deleted = await FavoriteCombinationService(session).delete(
        favorite_id=favorite_id, user_id=user.id, lottery_id=lottery_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Favorite was not found.")
    return Response(status_code=204)


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
            draw_count=request.draw_count,
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
        draw_ids=list(result.draw_ids or (result.draw_id,)),
        draw_count=result.draw_count,
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
            draw_count=request.draw_count,
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
        draw_ids=list(result.draw_ids or (result.draw_id,)),
        draw_count=result.draw_count,
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
    settings: Annotated[Settings, Depends(get_settings)],
) -> PurchaseResponse:
    if lottery_code not in PLAYABLE_LOTTERY_CODES:
        raise HTTPException(status_code=404, detail="Lottery is not available.")
    service = (
        DailyTicketPurchaseService(session, lottery_code=lottery_code)
        if lottery_code in DAILY_LOTTERY_CODES
        else WeeklyTicketPurchaseService(session, lottery_code=lottery_code)
    )
    if not purchase_rate_limiter.allow(
        user.id, limit=settings.miniapp_purchase_requests_per_minute
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many purchase attempts. Please wait a minute.",
            headers={"Retry-After": "60"},
        )
    try:
        result = await service.purchase(
            user_id=user.id,
            combinations=[list(value) for value in request.combinations],
            idempotency_key=request.idempotency_key,
            draw_count=request.draw_count,
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
        draw_ids=list(result.draw_ids or (result.draw_id,)),
        draw_count=result.draw_count,
        ticket_ids=list(result.ticket_ids),
        total_cost=result.total_cost,
        balance_after=result.balance_after,
        already_processed=result.already_processed,
    )
