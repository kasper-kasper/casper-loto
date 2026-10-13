"""FastAPI application factory."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from k_loto import __version__
from k_loto.api.router import api_router
from k_loto.application.runtime_monitoring import runtime_monitoring
from k_loto.core.config import get_settings
from k_loto.core.logging import configure_logging
from k_loto.infrastructure.request_metrics import RequestMetricsMiddleware
from k_loto.infrastructure.scheduler import SchedulerRuntime


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run startup reconciliation and the periodic scheduler when enabled."""
    settings = get_settings()
    scheduler: SchedulerRuntime | None = None
    monitor: asyncio.Task[None] | None = None
    if settings.scheduler_enabled:
        scheduler = SchedulerRuntime(settings.scheduler_interval_seconds)
        await scheduler.start()
        app.state.scheduler = scheduler
        monitor = asyncio.create_task(
            runtime_monitoring.run(
                Path(settings.monitoring_backup_dir), settings.operational_stuck_minutes
            )
        )
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown()
        if monitor is not None:
            monitor.cancel()
            await asyncio.gather(monitor, return_exceptions=True)


def create_app() -> FastAPI:
    """Create an application instance without connecting to external services."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Casper Loto API",
        version=__version__,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(api_router)
    if settings.web_enabled:
        from k_loto.api.routes.web import router as web_router

        app.include_router(web_router)
    app.add_middleware(RequestMetricsMiddleware)
    return app


app = create_app()
