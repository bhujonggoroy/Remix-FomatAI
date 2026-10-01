"""Mistral AI Provider adapter implementation.

Supports Mistral Small, Mistral Large, Codestral, and open models using Mistral's REST API.
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


class MistralProvider(BaseAIProvider):
    """Adapter for Mistral AI models."""

    DEFAULT_MODEL = "mistral-small-latest"
    BASE_URL = "https://api.mistral.ai/v1"

    SUPPORTED_MODELS = [
        AIModelInfo(
            id="mistral-small-latest",
            name="Mistral Small",
            context_window=128000,
            supports_formatting=True,
            description="Cost-effective, highly accurate model for standard academic formatting.",
        ),
        AIModelInfo(
            id="mistral-large-latest",
            name="Mistral Large",
            context_window=128000,
            supports_formatting=True,
            description="Top-tier reasoning model for rigorous mathematical and logical editing.",
        ),
        AIModelInfo(
            id="codestral-latest",
            name="Codestral",
            context_window=256000,
            supports_formatting=True,
            description="Specialized in code, pseudocode, LaTeX syntax, and structured documents.",
        ),
        AIModelInfo(
            id="open-mistral-nemo",
            name="Mistral NeMo",
            context_window=128000,
            supports_formatting=True,
            description="Efficient 12B model built in collaboration with NVIDIA.",
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
            provider_id="mistral",
            base_url=self.BASE_URL,
            api_key=self._api_key,
        )
        self._discovered_models: Optional[List[AIModelInfo]] = None

    @property
    def provider_id(self) -> str:
        return "mistral"

    @property
    def provider_name(self) -> str:
        return "Mistral AI"

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def list_models(self, force_refresh: bool = False) -> List[AIModelInfo]:
        """Discovers models from Mistral /models endpoint."""
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
                if m_id and not any(x in m_id.lower() for x in ["embed", "moderation"]):
                    discovered.append(
                        AIModelInfo(
                            id=m_id,
                            name=item.get("name") or m_id,
                            context_window=item.get("max_context_length", 128000),
                            supports_formatting=True,
                            is_discovered=True,
                        )
                    )

            if discovered:
                discovered.sort(key=lambda x: (x.id != self.DEFAULT_MODEL, x.id))
                self._discovered_models = discovered
                return list(discovered)
        except Exception as exc:
            logger.warning(f"Mistral model discovery failed: {exc}. Using curated models.")

        return list(self.SUPPORTED_MODELS)

    def validate_configuration(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> ProviderValidationResult:
        """Validates Mistral credentials by querying /models."""
        target_key = api_key.strip() if api_key and api_key.strip() else self._api_key
        if not target_key:
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message="Mistral API key is missing. Set MISTRAL_API_KEY in server environment or provide per-request key.",
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
                message="Mistral API key and connectivity verified successfully.",
                latency_ms=round(latency, 1),
                discovered_models_count=count,
            )
        except Exception as exc:
            safe_msg = sanitize_credentials(str(exc), [target_key] if target_key else [])
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message=f"Mistral validation failed: {safe_msg}",
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
        """Submits generation request to Mistral /chat/completions."""
        if not self.is_enabled():
            raise ProviderDisabledError(
                message="Mistral provider is currently disabled.",
                provider=self.provider_id,
            )

        if not self.is_configured():
            raise ProviderConfigError(
                message="Mistral API key is not configured. Set MISTRAL_API_KEY in the server environment (.env).",
                code="MISTRAL_KEY_NOT_CONFIGURED",
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

        logger.info(f"Submitting request to Mistral [model: {target_model}]")

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
                message="Mistral returned empty completion choices.",
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
