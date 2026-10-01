"""FormatAI Multi-Provider AI Architecture Package.

Provides isolated adapters for Google Gemini, Groq, OpenRouter, Mistral, Cohere,
Hugging Face, OpenAI, and Custom OpenAI-compatible endpoints.
"""

from backend.providers.base import (
    BaseAIProvider,
    ProviderAuthError,
    ProviderConfigError,
    ProviderDisabledError,
    ProviderError,
    ProviderGenerateResult,
    ProviderModelNotFoundError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUpstreamError,
)
from backend.providers.cohere import CohereProvider
from backend.providers.custom_openai import CustomOpenAIProvider
from backend.providers.factory import ProviderFactory
from backend.providers.gemini import GeminiProvider
from backend.providers.groq import GroqProvider
from backend.providers.huggingface import HuggingFaceProvider
from backend.providers.mistral import MistralProvider
from backend.providers.openai import OpenAIProvider
from backend.providers.openrouter import OpenRouterProvider

__all__ = [
    "BaseAIProvider",
    "ProviderFactory",
    "GeminiProvider",
    "GroqProvider",
    "OpenRouterProvider",
    "MistralProvider",
    "CohereProvider",
    "HuggingFaceProvider",
    "OpenAIProvider",
    "CustomOpenAIProvider",
    "ProviderError",
    "ProviderConfigError",
    "ProviderAuthError",
    "ProviderDisabledError",
    "ProviderTimeoutError",
    "ProviderRateLimitError",
    "ProviderUpstreamError",
    "ProviderModelNotFoundError",
    "ProviderGenerateResult",
]
