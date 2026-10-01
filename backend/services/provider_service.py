"""Business logic for discovering, querying, and managing AI providers and models."""

from typing import List, Optional
from backend.core.config import Settings
from backend.core.logging import logger
from backend.models.provider import AIModelInfo, AIProviderInfo, ProviderValidationResult
from backend.providers.base import ProviderError
from backend.providers.factory import ProviderFactory


class ProviderService:
    """Manages multi-provider AI discovery, validation, and runtime status."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def get_provider_manifest(self) -> List[AIProviderInfo]:
        """Discovers all supported providers and reports their availability and enabled status."""
        manifest: List[AIProviderInfo] = []
        registered_ids = ProviderFactory.list_available_providers()

        for pid in registered_ids:
            try:
                provider = ProviderFactory.get_provider(pid, self._settings)
                if provider:
                    is_available = provider.is_configured()
                    is_enabled = provider.is_enabled()
                    default_m = provider.default_model

                    # For custom provider, include configured base_url
                    base_url = None
                    requires_base_url = False
                    if pid in ("custom", "custom_openai"):
                        requires_base_url = True
                        base_url = getattr(provider, "base_url", self._settings.CUSTOM_OPENAI_BASE_URL)

                    # Return supported models safely (never crashes if one provider's discovery fails)
                    try:
                        supported_models = provider.get_supported_models()
                    except Exception as err:
                        logger.warning(f"Could not load models for provider {pid}: {err}")
                        supported_models = []

                    manifest.append(
                        AIProviderInfo(
                            id=provider.provider_id,
                            name=provider.provider_name,
                            is_available=is_available,
                            is_enabled=is_enabled,
                            default_model=default_m,
                            supported_models=supported_models,
                            supports_model_discovery=True,
                            requires_base_url=requires_base_url,
                            base_url=base_url,
                        )
                    )
            except Exception as exc:
                # Provider isolation: A failure in one provider must NOT crash the entire application
                logger.error(f"Error inspecting provider '{pid}': {exc}")

        return manifest

    def get_provider_info(self, provider_id: str) -> Optional[AIProviderInfo]:
        """Returns metadata for a single provider."""
        provider = ProviderFactory.get_provider(provider_id, self._settings)
        if not provider:
            return None

        requires_base_url = provider_id.lower() in ("custom", "custom_openai")
        base_url = getattr(provider, "base_url", None) if requires_base_url else None

        return AIProviderInfo(
            id=provider.provider_id,
            name=provider.provider_name,
            is_available=provider.is_configured(),
            is_enabled=provider.is_enabled(),
            default_model=provider.default_model,
            supported_models=provider.list_models(),
            supports_model_discovery=True,
            requires_base_url=requires_base_url,
            base_url=base_url,
        )

    def discover_models(self, provider_id: str, force_refresh: bool = True) -> List[AIModelInfo]:
        """Triggers model discovery for a specific provider adapter."""
        provider = ProviderFactory.get_provider(provider_id, self._settings)
        if not provider:
            raise ProviderError(
                message=f"Unknown AI provider: '{provider_id}'",
                code="UNKNOWN_PROVIDER",
                status_code=404,
            )

        return provider.list_models(force_refresh=force_refresh)

    def validate_provider(
        self,
        provider_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> ProviderValidationResult:
        """Validates configuration and network connectivity for a provider adapter."""
        provider = ProviderFactory.get_provider(
            provider_id=provider_id,
            settings=self._settings,
            override_api_key=api_key,
            override_base_url=base_url,
        )
        if not provider:
            return ProviderValidationResult(
                provider_id=provider_id,
                is_valid=False,
                message=f"Unknown AI provider: '{provider_id}'",
            )

        return provider.validate_configuration(api_key=api_key, base_url=base_url)

    def toggle_provider(self, provider_id: str, enabled: bool) -> bool:
        """Enables or disables a provider in the runtime registry."""
        norm = provider_id.strip().lower()
        if norm not in ProviderFactory.list_available_providers():
            raise ProviderError(
                message=f"Unknown AI provider: '{provider_id}'",
                code="UNKNOWN_PROVIDER",
                status_code=404,
            )

        ProviderFactory.set_provider_enabled(norm, enabled)
        return enabled
