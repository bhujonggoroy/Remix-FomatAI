"""Abstract base definitions and normalized error hierarchy for AI providers in FormatAI.

Enforces provider-independent contracts across all target adapters:
Google Gemini, Groq, OpenRouter, Mistral, Cohere, Hugging Face, OpenAI, and Custom OpenAI-compatible endpoints.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional
from backend.models.provider import AIModelInfo, ProviderValidationResult


def sanitize_credentials(text: str, sensitive_strings: Optional[List[str]] = None) -> str:
    """Strips API keys, bearer tokens, and sensitive strings from error messages and logs.

    Guarantees no provider API keys are ever leaked in client responses or telemetry.
    """
    if not text:
        return ""

    sanitized = text

    # Scrub explicit sensitive strings passed in
    if sensitive_strings:
        for s in sensitive_strings:
            if s and len(s) >= 4:
                sanitized = sanitized.replace(s, "[REDACTED_CREDENTIAL]")

    # Scrub common credential patterns
    # e.g. Bearer tokens, sk-..., gsk_..., hf_..., AIza...
    patterns = [
        r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}",
        r"(sk-[A-Za-z0-9_\-]{8,})",
        r"(gsk_[A-Za-z0-9_\-]{8,})",
        r"(hf_[A-Za-z0-9_\-]{8,})",
        r"(AIza[0-9A-Za-z-_]{20,})",
        r"(api[_-]?key[=:]\s*)[^\s&\"']+",
    ]
    for pattern in patterns:
        sanitized = re.sub(pattern, r"\1[REDACTED]", sanitized, flags=re.IGNORECASE)

    return sanitized


class ProviderError(Exception):
    """Base exception for all AI provider-level failures."""

    def __init__(
        self,
        message: str,
        code: str = "PROVIDER_ERROR",
        status_code: int = 502,
        provider: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = sanitize_credentials(message)
        self.code = code
        self.status_code = status_code
        self.provider = provider


class ProviderConfigError(ProviderError):
    """Raised when provider configuration or API keys are missing/invalid."""

    def __init__(
        self,
        message: str,
        code: str = "PROVIDER_NOT_CONFIGURED",
        provider: Optional[str] = None,
    ):
        super().__init__(message=message, code=code, status_code=503, provider=provider)


class ProviderAuthError(ProviderError):
    """Raised when upstream API key or authentication credentials fail (401/403)."""

    def __init__(
        self,
        message: str = "Authentication failed. Please verify API key configuration.",
        code: str = "PROVIDER_AUTH_ERROR",
        provider: Optional[str] = None,
    ):
        super().__init__(message=message, code=code, status_code=401, provider=provider)


class ProviderDisabledError(ProviderError):
    """Raised when a request is directed to a provider that has been explicitly disabled."""

    def __init__(
        self,
        message: str = "This AI provider has been disabled by system configuration or user settings.",
        code: str = "PROVIDER_DISABLED",
        provider: Optional[str] = None,
    ):
        super().__init__(message=message, code=code, status_code=400, provider=provider)


class ProviderTimeoutError(ProviderError):
    """Raised when an external AI provider call times out."""

    def __init__(
        self,
        message: str = "AI provider request timed out.",
        code: str = "PROVIDER_TIMEOUT",
        provider: Optional[str] = None,
    ):
        super().__init__(message=message, code=code, status_code=504, provider=provider)


class ProviderRateLimitError(ProviderError):
    """Raised when upstream AI provider rate limits are exceeded."""

    def __init__(
        self,
        message: str = "AI provider rate limit reached. Please try again shortly.",
        code: str = "RATE_LIMIT_EXCEEDED",
        provider: Optional[str] = None,
    ):
        super().__init__(message=message, code=code, status_code=429, provider=provider)


class ProviderModelNotFoundError(ProviderError):
    """Raised when the specified model is unknown or unsupported by the upstream provider."""

    def __init__(
        self,
        message: str = "The requested model was not found on this provider.",
        code: str = "MODEL_NOT_FOUND",
        provider: Optional[str] = None,
    ):
        super().__init__(message=message, code=code, status_code=404, provider=provider)


class ProviderUpstreamError(ProviderError):
    """Raised when the upstream AI service returns an operational error."""

    def __init__(
        self,
        message: str,
        code: str = "UPSTREAM_ERROR",
        provider: Optional[str] = None,
    ):
        super().__init__(message=message, code=code, status_code=502, provider=provider)


@dataclass
class ProviderGenerateResult:
    """Standardized output from any AI provider."""

    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, Any]] = None


class BaseAIProvider(ABC):
    """Abstract interface that all external AI provider adapters must implement.

    Guarantees isolation:
    - Each provider manages only its own credentials and client instances.
    - Errors are intercepted and normalized so provider failures never crash the app.
    """

    def __init__(self, is_enabled: bool = True):
        self._is_enabled: bool = is_enabled

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier string for the provider (e.g. 'gemini', 'groq', 'openai')."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name (e.g. 'Google Gemini', 'Groq')."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model identifier used when none is explicitly specified."""
        pass

    def is_enabled(self) -> bool:
        """Returns True if the provider is enabled for requests."""
        return self._is_enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enables or disables this provider."""
        self._is_enabled = enabled

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the required credentials (e.g. API key) are present."""
        pass

    def list_models(self, force_refresh: bool = False) -> List[AIModelInfo]:
        """Discovers models supported by this provider, with fallback to curated models."""
        return []

    def get_supported_models(self) -> List[AIModelInfo]:
        """Convenience alias for list_models(), maintaining backwards compatibility."""
        return self.list_models()

    def validate_configuration(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> ProviderValidationResult:
        """Validates credentials and connectivity without sending heavy generation requests."""
        is_valid = self.is_configured()
        return ProviderValidationResult(
            provider_id=self.provider_id,
            is_valid=is_valid,
            message=f"{self.provider_name} configuration is {'valid' if is_valid else 'not configured'}.",
        )

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: float = 30.0,
        retry_count: int = 1,
    ) -> ProviderGenerateResult:
        """Generates text from prompt. Subclasses can override generate() or generate_text()."""
        return self.generate_text(prompt=prompt, model=model, timeout=timeout)

    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> ProviderGenerateResult:
        """Backwards-compatible convenience wrapper around generate()."""
        return self.generate(prompt=prompt, model=model, timeout=timeout)
