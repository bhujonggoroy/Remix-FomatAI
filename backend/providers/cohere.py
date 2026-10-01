"""Cohere AI Provider adapter implementation.

Supports Command R+, Command R, and Cohere v2 Chat API.
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


class CohereProvider(BaseAIProvider):
    """Adapter for Cohere foundational language models."""

    DEFAULT_MODEL = "command-r-plus-08-2024"
    BASE_URL = "https://api.cohere.com/v2"
    V1_BASE_URL = "https://api.cohere.com/v1"

    SUPPORTED_MODELS = [
        AIModelInfo(
            id="command-r-plus-08-2024",
            name="Command R+ (Aug 2024)",
            context_window=128000,
            supports_formatting=True,
            description="Enterprise-grade model with world-class multilingual synthesis and RAG support.",
        ),
        AIModelInfo(
            id="command-r-08-2024",
            name="Command R (Aug 2024)",
            context_window=128000,
            supports_formatting=True,
            description="Fast, cost-efficient model optimized for document processing and summarization.",
        ),
        AIModelInfo(
            id="command-r7b-12-2024",
            name="Command R7B",
            context_window=128000,
            supports_formatting=True,
            description="Lightweight 7B parameter reasoning engine.",
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
            provider_id="cohere",
            base_url=self.BASE_URL,
            api_key=self._api_key,
        )
        self._discovered_models: Optional[List[AIModelInfo]] = None

    @property
    def provider_id(self) -> str:
        return "cohere"

    @property
    def provider_name(self) -> str:
        return "Cohere"

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def list_models(self, force_refresh: bool = False) -> List[AIModelInfo]:
        """Queries Cohere models endpoint or returns curated list."""
        if self._discovered_models and not force_refresh:
            return list(self._discovered_models)

        if not force_refresh or not self.is_configured():
            return list(self.SUPPORTED_MODELS)

        try:
            # Query v1 models endpoint
            data = self._http.request(
                method="GET",
                path="models",
                override_base_url=self.V1_BASE_URL,
                params={"endpoint": "chat"},
                timeout=8.0,
                retries=0,
            )
            items = data.get("models", [])
            discovered: List[AIModelInfo] = []
            for item in items:
                m_name = item.get("name")
                if m_name and "command" in m_name.lower():
                    discovered.append(
                        AIModelInfo(
                            id=m_name,
                            name=item.get("display_name") or m_name,
                            context_window=item.get("context_length", 128000),
                            supports_formatting=True,
                            is_discovered=True,
                        )
                    )

            if discovered:
                discovered.sort(key=lambda x: (x.id != self.DEFAULT_MODEL, x.id))
                self._discovered_models = discovered
                return list(discovered)
        except Exception as exc:
            logger.warning(f"Cohere model discovery failed: {exc}. Using curated models.")

        return list(self.SUPPORTED_MODELS)

    def validate_configuration(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> ProviderValidationResult:
        """Validates Cohere credentials by probing the models endpoint."""
        target_key = api_key.strip() if api_key and api_key.strip() else self._api_key
        if not target_key:
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message="Cohere API key is missing. Set COHERE_API_KEY in server environment or provide per-request key.",
            )

        start = time.time()
        try:
            data = self._http.request(
                method="GET",
                path="models",
                override_base_url=self.V1_BASE_URL,
                override_key=target_key,
                timeout=6.0,
                retries=0,
            )
            count = len(data.get("models", []))
            latency = (time.time() - start) * 1000.0
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=True,
                message="Cohere API key and connectivity verified successfully.",
                latency_ms=round(latency, 1),
                discovered_models_count=count,
            )
        except Exception as exc:
            safe_msg = sanitize_credentials(str(exc), [target_key] if target_key else [])
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message=f"Cohere validation failed: {safe_msg}",
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
        """Submits chat request to Cohere v2 Chat API."""
        if not self.is_enabled():
            raise ProviderDisabledError(
                message="Cohere provider is currently disabled.",
                provider=self.provider_id,
            )

        if not self.is_configured():
            raise ProviderConfigError(
                message="Cohere API key is not configured. Set COHERE_API_KEY in the server environment (.env).",
                code="COHERE_KEY_NOT_CONFIGURED",
                provider=self.provider_id,
            )

        target_model = model or self.default_model

        messages: List[Dict[str, Any]] = []
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

        logger.info(f"Submitting request to Cohere [model: {target_model}]")

        response = self._http.request(
            method="POST",
            path="chat",
            json_body=body,
            timeout=timeout,
            retries=retry_count,
        )

        message_obj = response.get("message", {})
        content_items = message_obj.get("content", [])

        # Extract text from content blocks
        extracted_text = ""
        for item in content_items:
            if isinstance(item, dict) and item.get("type") == "text":
                extracted_text += item.get("text", "")
            elif isinstance(item, str):
                extracted_text += item

        usage = response.get("usage", {})

        return ProviderGenerateResult(
            content=extracted_text,
            model=target_model,
            provider=self.provider_id,
            usage=usage,
        )
