"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from k_loto import __version__
from k_loto.api.router import api_router
from k_loto.core.config import get_settings
from k_loto.core.logging import configure_logging
from k_loto.infrastructure.scheduler import SchedulerRuntime


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run startup reconciliation and the periodic scheduler when enabled."""
    settings = get_settings()
    scheduler: SchedulerRuntime | None = None
    if settings.scheduler_enabled:
        scheduler = SchedulerRuntime(settings.scheduler_interval_seconds)
        await scheduler.start()
        app.state.scheduler = scheduler
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown()


def create_app() -> FastAPI:
    """Create an application instance without connecting to external services."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="K-Loto API",
        version=__version__,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(api_router)
    return app


app = create_app()
