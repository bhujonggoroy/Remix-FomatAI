"""OpenRouter AI Provider adapter implementation.

Unified interface to hundreds of foundational models (Claude, Llama, Gemini, DeepSeek, Mistral) via OpenRouter.
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


class OpenRouterProvider(BaseAIProvider):
    """Adapter for OpenRouter unified multi-model routing API."""

    DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"
    BASE_URL = "https://openrouter.ai/api/v1"

    SUPPORTED_MODELS = [
        AIModelInfo(
            id="meta-llama/llama-3.3-70b-instruct",
            name="Meta Llama 3.3 70B Instruct",
            context_window=131072,
            supports_formatting=True,
            description="High-performance open weights model with exceptional STEM capabilities.",
        ),
        AIModelInfo(
            id="anthropic/claude-3.5-sonnet",
            name="Anthropic Claude 3.5 Sonnet",
            context_window=200000,
            supports_formatting=True,
            description="Leading model for complex academic papers, literature surveys, and nuanced editing.",
        ),
        AIModelInfo(
            id="google/gemini-2.0-flash-001",
            name="Google Gemini 2.0 Flash",
            context_window=1048576,
            supports_formatting=True,
            description="Ultra-fast Google Gemini model routed via OpenRouter.",
        ),
        AIModelInfo(
            id="deepseek/deepseek-chat",
            name="DeepSeek V3",
            context_window=64000,
            supports_formatting=True,
            description="Advanced open reasoning and mathematics model.",
        ),
        AIModelInfo(
            id="mistralai/mistral-large-2411",
            name="Mistral Large 2411",
            context_window=128000,
            supports_formatting=True,
            description="Mistral's flagship multilingual reasoning engine.",
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
            provider_id="openrouter",
            base_url=self.BASE_URL,
            api_key=self._api_key,
            default_headers={
                "HTTP-Referer": "https://formatai.app",
                "X-Title": "FormatAI Academic Typesetter",
            },
        )
        self._discovered_models: Optional[List[AIModelInfo]] = None

    @property
    def provider_id(self) -> str:
        return "openrouter"

    @property
    def provider_name(self) -> str:
        return "OpenRouter"

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def list_models(self, force_refresh: bool = False) -> List[AIModelInfo]:
        """Queries OpenRouter /models endpoint for top recommended academic models."""
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
            items = data.get("data", [])
            discovered: List[AIModelInfo] = []
            for item in items:
                m_id = item.get("id")
                name = item.get("name", m_id)
                context = item.get("context_length", 128000)
                # Keep popular text models
                if m_id and not any(x in m_id.lower() for x in ["image", "flux", "whisper", "embedding"]):
                    discovered.append(
                        AIModelInfo(
                            id=m_id,
                            name=name,
                            context_window=context,
                            supports_formatting=True,
                            is_discovered=True,
                        )
                    )

            if discovered:
                # Prioritize curated models
                discovered.sort(
                    key=lambda x: (
                        0 if x.id == self.DEFAULT_MODEL else 1 if "claude" in x.id else 2 if "llama" in x.id else 3,
                        x.id,
                    )
                )
                self._discovered_models = discovered[:40]  # Keep top 40 relevant models
                return list(self._discovered_models)
        except Exception as exc:
            logger.warning(f"OpenRouter model discovery failed: {exc}. Using curated list.")

        return list(self.SUPPORTED_MODELS)

    def validate_configuration(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> ProviderValidationResult:
        """Validates OpenRouter API key via /models endpoint."""
        target_key = api_key.strip() if api_key and api_key.strip() else self._api_key
        if not target_key:
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message="OpenRouter API key is missing. Set OPENROUTER_API_KEY in server environment or provide per-request key.",
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
                message="OpenRouter credentials and connectivity verified successfully.",
                latency_ms=round(latency, 1),
                discovered_models_count=count,
            )
        except Exception as exc:
            safe_msg = sanitize_credentials(str(exc), [target_key] if target_key else [])
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message=f"OpenRouter validation failed: {safe_msg}",
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
        """Submits generation request to OpenRouter chat completions."""
        if not self.is_enabled():
            raise ProviderDisabledError(
                message="OpenRouter provider is currently disabled.",
                provider=self.provider_id,
            )

        if not self.is_configured():
            raise ProviderConfigError(
                message="OpenRouter API key is not configured. Set OPENROUTER_API_KEY in the server environment (.env).",
                code="OPENROUTER_KEY_NOT_CONFIGURED",
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

        logger.info(f"Submitting request to OpenRouter [model: {target_model}]")

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
                message="OpenRouter returned empty completion choices.",
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
