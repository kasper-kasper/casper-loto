"""Top-level API router."""

from fastapi import APIRouter

from k_loto.api.routes.admin import router as admin_router
from k_loto.api.routes.health import router as health_router
from k_loto.api.routes.miniapp import router as miniapp_router
from k_loto.api.routes.publications import router as publications_router
from k_loto.api.routes.web import router as web_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(admin_router)
api_router.include_router(miniapp_router)
api_router.include_router(web_router)
api_router.include_router(publications_router)
