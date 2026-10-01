"""Health check and system status route endpoints."""

from fastapi import APIRouter, Depends
from backend.api.deps import get_health_service
from backend.models.health import HealthResponse, RootResponse
from backend.services.health_service import HealthService

router = APIRouter(tags=["System & Health"])


@router.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns the operational status of the FormatAI Python backend.",
)
def get_health(
    service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    """Route handler delegating health verification to HealthService."""
    return service.get_health_status()


@router.get(
    "/",
    response_model=RootResponse,
    summary="Root Service Information",
    description="Returns overview information indicating that the FastAPI backend is online.",
)
def get_root(
    service: HealthService = Depends(get_health_service),
) -> RootResponse:
    """Route handler delegating root status generation to HealthService."""
    return service.get_root_status()
