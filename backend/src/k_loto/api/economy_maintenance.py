"""Public pause status and an HTTP gate before identity creation or handlers."""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from k_loto.application.economy import is_paused
from k_loto.infrastructure.database.session import session_factory

router = APIRouter()
STATUS_PATH = "/api/v1/miniapp/maintenance"


@router.get(STATUS_PATH)
async def maintenance_status() -> JSONResponse:
    async with session_factory() as session:
        paused = await is_paused(session)
    return JSONResponse(
        {"maintenance": paused, "message": "Обновляем экономику"},
        headers={"Cache-Control": "no-store"},
    )


async def maintenance_gate(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    path = request.url.path
    if path.startswith("/api/v1/miniapp") and path.rstrip("/") != STATUS_PATH:
        async with session_factory() as session:
            paused = await is_paused(session)
        if paused:
            return JSONResponse(
                {"maintenance": True, "detail": "Обновляем экономику"},
                status_code=503,
                headers={"Cache-Control": "no-store"},
            )
    if (
        path.startswith("/api/v1/admin/")
        and request.headers.get("X-Economy-Scope") == "archive"
        and request.method not in {"GET", "HEAD", "OPTIONS"}
        and "/auth/" not in path
    ):
        return JSONResponse(
            {"detail": "Архив старой экономики доступен только для просмотра."},
            status_code=403,
        )
    return await call_next(request)
