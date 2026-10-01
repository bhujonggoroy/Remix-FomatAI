"""AI Provider text generation and multi-provider management routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from backend.api.deps import get_ai_service, get_provider_service
from backend.models.ai import (
    AIGenerateRequest,
    AIGenerateResponse,
    AIErrorDetail,
    AIErrorResponse,
)
from backend.models.provider import (
    AIModelInfo,
    AIProviderInfo,
    ProviderToggleRequest,
    ProviderValidationRequest,
    ProviderValidationResult,
)
from backend.providers.base import ProviderError
from backend.services.ai_service import AIService
from backend.services.provider_service import ProviderService

router = APIRouter(prefix="/api/ai", tags=["AI Generation & Multi-Provider Architecture"])


@router.post(
    "/generate",
    response_model=AIGenerateResponse,
    response_model_exclude_none=True,
    responses={
        400: {"model": AIErrorResponse, "description": "Validation, disabled provider, or invalid request"},
        401: {"model": AIErrorResponse, "description": "Authentication failure with upstream provider"},
        404: {"model": AIErrorResponse, "description": "Specified model was not found"},
        429: {"model": AIErrorResponse, "description": "Rate limit exceeded"},
        502: {"model": AIErrorResponse, "description": "Upstream AI provider error"},
        503: {"model": AIErrorResponse, "description": "Provider not configured"},
        504: {"model": AIErrorResponse, "description": "Provider request timeout"},
    },
    summary="Generate text via selected AI provider adapter",
    description="Submits prompt to selected provider (Gemini, Groq, OpenRouter, Mistral, Cohere, Hugging Face, OpenAI, Custom) and returns standardized content.",
)
def generate_ai_text(
    payload: AIGenerateRequest,
    ai_service: AIService = Depends(get_ai_service),
):
    """Executes AI generation request, delegating logic to AIService."""
    try:
        return ai_service.generate(payload)
    except ProviderError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=AIErrorResponse(
                success=False,
                error=AIErrorDetail(
                    code=exc.code,
                    message=exc.message,
                    provider=exc.provider,
                ),
            ).model_dump(),
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=AIErrorResponse(
                success=False,
                error=AIErrorDetail(
                    code="INVALID_REQUEST",
                    message=str(exc),
                    provider=payload.provider,
                ),
            ).model_dump(),
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=AIErrorResponse(
                success=False,
                error=AIErrorDetail(
                    code="INTERNAL_SERVER_ERROR",
                    message="An unexpected error occurred while processing the AI request.",
                    provider=payload.provider,
                ),
            ).model_dump(),
        )


@router.get(
    "/providers",
    response_model=List[AIProviderInfo],
    summary="List all integrated AI providers",
    description="Returns registry of all available providers, their enabled state, configuration readiness, and models.",
)
def list_providers(
    provider_service: ProviderService = Depends(get_provider_service),
):
    """Returns the multi-provider catalog with availability status."""
    return provider_service.get_provider_manifest()


@router.get(
    "/providers/{provider_id}",
    response_model=AIProviderInfo,
    responses={404: {"description": "Provider not found"}},
    summary="Get single provider details",
)
def get_provider_details(
    provider_id: str,
    provider_service: ProviderService = Depends(get_provider_service),
):
    """Returns metadata and models for a specific AI provider."""
    info = provider_service.get_provider_info(provider_id)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' is not registered in the system.",
        )
    return info


@router.get(
    "/providers/{provider_id}/models",
    response_model=List[AIModelInfo],
    responses={404: {"description": "Provider not found"}},
    summary="Discover models from provider",
    description="Queries the upstream provider's /models endpoint where supported, returning freshly discovered models.",
)
def discover_provider_models(
    provider_id: str,
    force_refresh: bool = Query(default=True, description="Force re-querying upstream provider"),
    provider_service: ProviderService = Depends(get_provider_service),
):
    """Triggers dynamic model discovery for the target provider adapter."""
    try:
        return provider_service.discover_models(provider_id, force_refresh=force_refresh)
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post(
    "/providers/{provider_id}/validate",
    response_model=ProviderValidationResult,
    summary="Validate provider configuration",
    description="Tests API credentials and connection health for a specific provider without full generation.",
)
def validate_provider_configuration(
    provider_id: str,
    payload: ProviderValidationRequest = ProviderValidationRequest(),
    provider_service: ProviderService = Depends(get_provider_service),
):
    """Tests credentials and reports latency and model count."""
    return provider_service.validate_provider(
        provider_id=provider_id,
        api_key=payload.api_key,
        base_url=payload.base_url,
    )


@router.post(
    "/providers/{provider_id}/toggle",
    summary="Enable or disable a provider",
    description="Enables or disables an AI provider in the runtime registry. Disabled providers will reject requests.",
)
def toggle_provider_status(
    provider_id: str,
    payload: ProviderToggleRequest,
    provider_service: ProviderService = Depends(get_provider_service),
):
    """Toggles enabled state for the target provider."""
    try:
        enabled = provider_service.toggle_provider(provider_id, payload.enabled)
        return {
            "success": True,
            "provider_id": provider_id,
            "enabled": enabled,
            "message": f"Provider '{provider_id}' is now {'enabled' if enabled else 'disabled'}.",
        }
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
