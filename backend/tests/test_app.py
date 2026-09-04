"""Foundation tests for the application factory."""

from typing import cast

from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.api.routes.health import HealthResponse, health
from k_loto.main import create_app


def test_application_metadata() -> None:
    app = create_app()

    assert app.title == "K-Loto API"
    assert app.version == "1.11.1"


def test_health_route_is_registered() -> None:
    app = create_app()
    paths = app.openapi()["paths"]

    assert "/health" in paths


class HealthySession:
    async def execute(self, _statement: object) -> None:
        return None


class UnavailableSession:
    async def execute(self, _statement: object) -> None:
        raise SQLAlchemyError("database unavailable")


async def test_health_reports_healthy_database() -> None:
    result = await health(cast(AsyncSession, HealthySession()))

    assert isinstance(result, HealthResponse)
    assert result.status == "ok"
    assert result.database.status == "ok"


async def test_health_reports_database_outage() -> None:
    result = await health(cast(AsyncSession, UnavailableSession()))

    assert isinstance(result, JSONResponse)
    assert result.status_code == 503
