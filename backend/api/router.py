"""Main API Router aggregating all domain sub-routers."""

from fastapi import APIRouter
from backend.api.routes.health import router as health_router
from backend.api.routes.ai import router as ai_router
from backend.api.routes.document import router as document_router
from backend.api.routes.skills import router as skills_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(ai_router)
api_router.include_router(document_router)
api_router.include_router(skills_router)
