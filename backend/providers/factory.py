"""Factory to instantiate, configure, and manage AI provider adapters dynamically.

Enforces provider isolation, secure credential scoping, and enable/disable state management.
"""

from typing import Dict, List, Optional, Type
from backend.core.config import Settings
from backend.providers.base import BaseAIProvider
from backend.providers.gemini import GeminiProvider
from backend.providers.groq import GroqProvider
from backend.providers.openrouter import OpenRouterProvider
from backend.providers.mistral import MistralProvider
from backend.providers.cohere import CohereProvider
from backend.providers.huggingface import HuggingFaceProvider
from backend.providers.openai import OpenAIProvider
from backend.providers.custom_openai import CustomOpenAIProvider


class ProviderFactory:
    """Manages AI provider adapter registration, instantiation, and runtime status."""

    _registry: Dict[str, Type[BaseAIProvider]] = {
        "gemini": GeminiProvider,
        "groq": GroqProvider,
        "openrouter": OpenRouterProvider,
        "mistral": MistralProvider,
        "cohere": CohereProvider,
        "huggingface": HuggingFaceProvider,
        "openai": OpenAIProvider,
        "custom": CustomOpenAIProvider,
        "custom_openai": CustomOpenAIProvider,  # Alias
    }

    # In-memory runtime state for provider enable/disable flags
    _disabled_providers: set[str] = set()

    @classmethod
    def get_provider(
        cls,
        provider_id: str,
        settings: Settings,
        override_api_key: Optional[str] = None,
        override_base_url: Optional[str] = None,
    ) -> Optional[BaseAIProvider]:
        """Instantiates an isolated provider adapter with safe credentials from settings or request override."""
        normalized_id = provider_id.strip().lower()
        provider_class = cls._registry.get(normalized_id)
        if not provider_class:
            return None

        # Determine enabled state
        is_disabled = (
            normalized_id in cls._disabled_providers
            or normalized_id in [p.lower() for p in settings.DISABLED_AI_PROVIDERS]
        )
        is_enabled = not is_disabled

        # Instantiation with scoped credentials - each provider receives ONLY its own key!
        if normalized_id == "gemini":
            key = override_api_key or settings.GEMINI_API_KEY
            return GeminiProvider(api_key=key, is_enabled=is_enabled)

        elif normalized_id == "groq":
            key = override_api_key or settings.GROQ_API_KEY
            return GroqProvider(api_key=key, is_enabled=is_enabled)

        elif normalized_id == "openrouter":
            key = override_api_key or settings.OPENROUTER_API_KEY
            return OpenRouterProvider(api_key=key, is_enabled=is_enabled)

        elif normalized_id == "mistral":
            key = override_api_key or settings.MISTRAL_API_KEY
            return MistralProvider(api_key=key, is_enabled=is_enabled)

        elif normalized_id == "cohere":
            key = override_api_key or settings.COHERE_API_KEY
            return CohereProvider(api_key=key, is_enabled=is_enabled)

        elif normalized_id == "huggingface":
            key = override_api_key or settings.HUGGINGFACE_API_KEY or settings.HF_TOKEN
            return HuggingFaceProvider(api_key=key, is_enabled=is_enabled)

        elif normalized_id == "openai":
            key = override_api_key or settings.OPENAI_API_KEY
            return OpenAIProvider(api_key=key, is_enabled=is_enabled)

        elif normalized_id in ("custom", "custom_openai"):
            key = override_api_key or settings.CUSTOM_OPENAI_API_KEY
            base_url = override_base_url or settings.CUSTOM_OPENAI_BASE_URL
            return CustomOpenAIProvider(base_url=base_url, api_key=key, is_enabled=is_enabled)

        # Fallback default instantiation for custom extensions
        return provider_class(is_enabled=is_enabled)  # type: ignore

    @classmethod
    def list_available_providers(cls) -> List[str]:
        """Returns ordered list of primary canonical registered provider IDs."""
        canonical = [
            "gemini",
            "groq",
            "openrouter",
            "mistral",
            "cohere",
            "huggingface",
            "openai",
            "custom",
        ]
        return canonical

    @classmethod
    def is_provider_enabled(cls, provider_id: str, settings: Settings) -> bool:
        """Checks if a provider is currently enabled."""
        norm = provider_id.strip().lower()
        if norm in cls._disabled_providers:
            return False
        if norm in [p.lower() for p in settings.DISABLED_AI_PROVIDERS]:
            return False
        return True

    @classmethod
    def set_provider_enabled(cls, provider_id: str, enabled: bool) -> None:
        """Enables or disables a provider in the runtime registry."""
        norm = provider_id.strip().lower()
        if enabled:
            cls._disabled_providers.discard(norm)
        else:
            cls._disabled_providers.add(norm)
