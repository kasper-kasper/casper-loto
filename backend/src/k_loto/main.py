"""FastAPI application factory."""

from fastapi import FastAPI

from k_loto import __version__
from k_loto.api.router import api_router
from k_loto.core.config import get_settings
from k_loto.core.logging import configure_logging


def create_app() -> FastAPI:
    """Create an application instance without connecting to external services."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="K-Loto API",
        version=__version__,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
    )
    app.include_router(api_router)
    return app


app = create_app()
