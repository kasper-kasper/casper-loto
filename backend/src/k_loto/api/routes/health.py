"""Application health endpoints."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.api.dependencies import get_db_session

router = APIRouter(tags=["health"])


class ComponentHealth(BaseModel):
    """Health state of one component."""

    status: Literal["ok", "unavailable"]


class HealthResponse(BaseModel):
    """Aggregate application health state."""

    status: Literal["ok", "degraded"]
    application: ComponentHealth
    database: ComponentHealth


@router.get("/health", response_model=HealthResponse)
async def health(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HealthResponse | JSONResponse:
    """Report application liveness and database connectivity."""
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        payload = HealthResponse(
            status="degraded",
            application=ComponentHealth(status="ok"),
            database=ComponentHealth(status="unavailable"),
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )

    return HealthResponse(
        status="ok",
        application=ComponentHealth(status="ok"),
        database=ComponentHealth(status="ok"),
    )
