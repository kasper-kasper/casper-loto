"""Authenticated Telegram Mini App API."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.api.dependencies import (
    CurrentMiniAppUser,
    get_current_miniapp_user,
    get_db_session,
)
from k_loto.application.miniapp import (
    MiniAppDashboard,
    MiniAppLottery,
    MiniAppQueryService,
    MiniAppTicket,
)
from k_loto.application.weekly import WeeklyTicketPurchaseService
from k_loto.domain.enums import LotteryKind, TicketStatus
from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InvalidTicket,
    NoAvailableDraw,
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
    balance: int
    active_ticket_count: int
    lotteries: list[LotteryResponse]
    recent_results: list[TicketResponse]


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]


class PurchaseRequest(BaseModel):
    combinations: list[list[int]] = Field(min_length=1)
    idempotency_key: str = Field(min_length=1, max_length=100)


class PurchaseResponse(BaseModel):
    operation_id: UUID
    draw_id: UUID
    ticket_ids: list[UUID]
    total_cost: int
    balance_after: int
    already_processed: bool


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
        balance=item.balance,
        active_ticket_count=item.active_ticket_count,
        lotteries=[_lottery_response(value) for value in item.lotteries],
        recent_results=[_ticket_response(value) for value in item.recent_results],
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    user: Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardResponse:
    return _dashboard_response(await MiniAppQueryService(session).dashboard(user.id))


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
