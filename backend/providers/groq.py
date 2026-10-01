"""Groq AI Provider adapter implementation.

Provides high-speed inference for Llama, Mixtral, and Gemma models using Groq's OpenAI-compatible API.
"""

import time
from typing import Any, Dict, List, Optional
from backend.core.logging import logger
from backend.models.provider import AIModelInfo, ProviderValidationResult
from backend.providers.base import (
    BaseAIProvider,
    ProviderConfigError,
    ProviderDisabledError,
    ProviderGenerateResult,
    sanitize_credentials,
)
from backend.providers.http_adapter import ProviderHTTPClient


class GroqProvider(BaseAIProvider):
    """Adapter for Groq LPUs via OpenAI-compatible endpoints."""

    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    BASE_URL = "https://api.groq.com/openai/v1"

    SUPPORTED_MODELS = [
        AIModelInfo(
            id="llama-3.3-70b-versatile",
            name="Llama 3.3 70B Versatile",
            context_window=131072,
            supports_formatting=True,
            description="Flagship open model with excellent academic reasoning and citation accuracy.",
        ),
        AIModelInfo(
            id="llama-3.1-8b-instant",
            name="Llama 3.1 8B Instant",
            context_window=131072,
            supports_formatting=True,
            description="Ultra-low latency model ideal for rapid LaTeX formula cleanup.",
        ),
        AIModelInfo(
            id="mixtral-8x7b-32768",
            name="Mixtral 8x7B",
            context_window=32768,
            supports_formatting=True,
            description="High-throughput mixture of experts model.",
        ),
        AIModelInfo(
            id="gemma2-9b-it",
            name="Gemma 2 9B IT",
            context_window=8192,
            supports_formatting=True,
            description="Google Gemma 2 instruction tuned on Groq LPUs.",
        ),
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        is_enabled: bool = True,
        http_client: Optional[ProviderHTTPClient] = None,
    ):
        super().__init__(is_enabled=is_enabled)
        self._api_key = api_key.strip() if api_key and api_key.strip() else None
        self._http = http_client or ProviderHTTPClient(
            provider_id="groq",
            base_url=self.BASE_URL,
            api_key=self._api_key,
        )
        self._discovered_models: Optional[List[AIModelInfo]] = None

    @property
    def provider_id(self) -> str:
        return "groq"

    @property
    def provider_name(self) -> str:
        return "Groq"

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def list_models(self, force_refresh: bool = False) -> List[AIModelInfo]:
        """Discovers available models from Groq /models API or returns curated defaults."""
        if self._discovered_models and not force_refresh:
            return list(self._discovered_models)

        if not force_refresh or not self.is_configured():
            return list(self.SUPPORTED_MODELS)

        try:
            data = self._http.request(
                method="GET",
                path="models",
                timeout=8.0,
                retries=0,
            )
            model_items = data.get("data", [])
            discovered: List[AIModelInfo] = []
            for item in model_items:
                m_id = item.get("id")
                if m_id and not any(x in m_id.lower() for x in ["whisper", "guard", "audio"]):
                    discovered.append(
                        AIModelInfo(
                            id=m_id,
                            name=m_id,
                            context_window=item.get("context_window", 131072),
                            supports_formatting=True,
                            is_discovered=True,
                        )
                    )

            if discovered:
                # Sort so favorite default models appear first
                discovered.sort(key=lambda x: (x.id != self.DEFAULT_MODEL, x.id))
                self._discovered_models = discovered
                return list(discovered)
        except Exception as exc:
            logger.warning(f"Groq model discovery failed: {exc}. Using curated models.")

        return list(self.SUPPORTED_MODELS)

    def validate_configuration(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> ProviderValidationResult:
        """Validates Groq credentials via a fast /models probe."""
        target_key = api_key.strip() if api_key and api_key.strip() else self._api_key
        if not target_key:
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message="Groq API key is missing. Set GROQ_API_KEY in server environment or provide per-request key.",
            )

        start = time.time()
        try:
            data = self._http.request(
                method="GET",
                path="models",
                override_key=target_key,
                timeout=6.0,
                retries=0,
            )
            count = len(data.get("data", []))
            latency = (time.time() - start) * 1000.0
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=True,
                message="Groq API key and connectivity verified successfully.",
                latency_ms=round(latency, 1),
                discovered_models_count=count,
            )
        except Exception as exc:
            safe_msg = sanitize_credentials(str(exc), [target_key] if target_key else [])
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message=f"Groq validation failed: {safe_msg}",
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
        """Submits chat completion request to Groq."""
        if not self.is_enabled():
            raise ProviderDisabledError(
                message="Groq provider is currently disabled.",
                provider=self.provider_id,
            )

        if not self.is_configured():
            raise ProviderConfigError(
                message="Groq API key is not configured. Set GROQ_API_KEY in the server environment (.env).",
                code="GROQ_KEY_NOT_CONFIGURED",
                provider=self.provider_id,
            )

        target_model = model or self.default_model

        messages: List[Dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        body: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
        }
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        logger.info(f"Submitting request to Groq [model: {target_model}]")

        response = self._http.request(
            method="POST",
            path="chat/completions",
            json_body=body,
            timeout=timeout,
            retries=retry_count,
        )

        choices = response.get("choices", [])
        if not choices:
            raise ProviderConfigError(
                message="Groq returned empty completion choices.",
                provider=self.provider_id,
            )

        content = choices[0].get("message", {}).get("content", "")
        usage = response.get("usage")

        return ProviderGenerateResult(
            content=content,
            model=target_model,
            provider=self.provider_id,
            usage=usage,
        )
