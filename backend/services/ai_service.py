"""AI Service business logic layer.

Orchestrates AI generation requests through isolated provider abstractions (BaseAIProvider),
handling provider enable/disable checks, timeouts, retries, and explicit fallback routing.
"""

from typing import Optional
from backend.core.config import Settings
from backend.core.logging import logger
from backend.models.ai import AIGenerateRequest, AIGenerateResponse
from backend.providers.base import (
    BaseAIProvider,
    ProviderConfigError,
    ProviderDisabledError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUpstreamError,
)
from backend.providers.factory import ProviderFactory


class AIService:
    """Orchestrates AI generation requests through provider adapters."""

    def __init__(self, settings: Settings, provider: Optional[BaseAIProvider] = None):
        self._settings = settings
        self._override_provider = provider

    def _resolve_provider(
        self,
        provider_id: Optional[str],
        override_api_key: Optional[str] = None,
        override_base_url: Optional[str] = None,
    ) -> BaseAIProvider:
        """Resolves target provider instance from factory or injected provider with scoped credentials."""
        if self._override_provider is not None:
            return self._override_provider

        target_id = (provider_id or self._settings.DEFAULT_AI_PROVIDER).strip().lower()
        provider = ProviderFactory.get_provider(
            provider_id=target_id,
            settings=self._settings,
            override_api_key=override_api_key,
            override_base_url=override_base_url,
        )

        if not provider:
            raise ProviderError(
                message=f"Unsupported AI provider: '{target_id}'. Registered providers: {ProviderFactory.list_available_providers()}",
                code="UNSUPPORTED_PROVIDER",
                status_code=400,
            )

        return provider

    def generate(self, request: AIGenerateRequest) -> AIGenerateResponse:
        """Executes text generation using the resolved provider with retry and optional fallback."""
        primary_provider = self._resolve_provider(
            provider_id=request.provider,
            override_api_key=request.api_key,
            override_base_url=request.base_url,
        )

        # 1. Do not send a request to providers that the user has disabled
        if not primary_provider.is_enabled():
            raise ProviderDisabledError(
                message=f"Provider '{primary_provider.provider_name}' has been disabled.",
                provider=primary_provider.provider_id,
            )

        # 2. Check configuration (API key / Base URL)
        if not primary_provider.is_configured():
            raise ProviderConfigError(
                message=f"Provider '{primary_provider.provider_name}' is not configured with an API key in the server environment (.env) or request.",
                code="PROVIDER_NOT_CONFIGURED",
                provider=primary_provider.provider_id,
            )

        # Timeout and retry configuration
        timeout = request.timeout if request.timeout is not None else self._settings.DEFAULT_AI_TIMEOUT
        retries = request.retries if request.retries is not None else self._settings.DEFAULT_AI_MAX_RETRIES

        logger.info(
            f"AIService executing request [provider={primary_provider.provider_id}, model={request.model or primary_provider.default_model}, timeout={timeout}s]"
        )

        try:
            result = primary_provider.generate(
                prompt=request.prompt,
                model=request.model,
                system_instruction=request.system_instruction,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                timeout=timeout,
                retry_count=retries,
            )

            return AIGenerateResponse(
                success=True,
                provider=result.provider,
                model=result.model,
                content=result.content,
                fallback_used=None,
                usage=result.usage,
            )

        except (ProviderUpstreamError, ProviderTimeoutError, ProviderRateLimitError) as primary_error:
            # Fallback ONLY when explicitly configured by user/caller
            if request.fallback_provider and request.fallback_provider.strip().lower() != primary_provider.provider_id:
                fallback_id = request.fallback_provider.strip().lower()
                logger.warning(
                    f"Primary provider '{primary_provider.provider_id}' failed: {primary_error.message}. "
                    f"Engaging explicitly configured fallback provider: '{fallback_id}'"
                )

                try:
                    fallback_provider = self._resolve_provider(fallback_id)
                    if fallback_provider.is_enabled() and fallback_provider.is_configured():
                        fallback_result = fallback_provider.generate(
                            prompt=request.prompt,
                            model=request.fallback_model,
                            system_instruction=request.system_instruction,
                            temperature=request.temperature,
                            max_tokens=request.max_tokens,
                            timeout=timeout,
                            retry_count=retries,
                        )
                        return AIGenerateResponse(
                            success=True,
                            provider=fallback_result.provider,
                            model=fallback_result.model,
                            content=fallback_result.content,
                            fallback_used=True,
                            original_provider=primary_provider.provider_id,
                            usage=fallback_result.usage,
                        )
                except Exception as fb_exc:
                    logger.error(f"Fallback provider '{fallback_id}' also failed: {fb_exc}")
                    # Raise original primary error with fallback note
                    raise ProviderUpstreamError(
                        message=f"{primary_error.message} (Fallback provider '{fallback_id}' also failed: {fb_exc})",
                        provider=primary_provider.provider_id,
                    ) from primary_error

            # No fallback explicitly configured: re-raise the normalized primary error directly
            raise
