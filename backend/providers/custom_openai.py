"""Custom OpenAI-compatible AI Provider adapter implementation.

Connects to any OpenAI-compatible API endpoint:
- Local instances (Ollama, LM Studio, vLLM, LocalAI, Text Generation WebUI)
- Custom self-hosted servers or enterprise gateways
- Any proxy adhering to OpenAI's /chat/completions and /models specifications.
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


class CustomOpenAIProvider(BaseAIProvider):
    """Adapter for custom, self-hosted, or local OpenAI-compatible endpoints."""

    DEFAULT_MODEL = "custom-model"
    DEFAULT_BASE_URL = "http://localhost:11434/v1"

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        is_enabled: bool = True,
        http_client: Optional[ProviderHTTPClient] = None,
    ):
        super().__init__(is_enabled=is_enabled)
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._api_key = api_key.strip() if api_key and api_key.strip() else None
        self._http = http_client or ProviderHTTPClient(
            provider_id="custom",
            base_url=self._base_url,
            api_key=self._api_key,
        )
        self._discovered_models: Optional[List[AIModelInfo]] = None

    @property
    def provider_id(self) -> str:
        return "custom"

    @property
    def provider_name(self) -> str:
        return "Custom OpenAI-Compatible"

    @property
    def default_model(self) -> str:
        if self._discovered_models and len(self._discovered_models) > 0:
            return self._discovered_models[0].id
        return self.DEFAULT_MODEL

    @property
    def base_url(self) -> str:
        return self._base_url

    def set_base_url(self, url: str) -> None:
        """Updates the active base URL."""
        if url and url.strip():
            self._base_url = url.strip().rstrip("/")
            self._http.base_url = self._base_url
            self._discovered_models = None

    def is_configured(self) -> bool:
        """Custom endpoint is considered configured if a base URL is specified (API key is optional for local servers)."""
        return bool(self._base_url)

    def list_models(self, force_refresh: bool = False) -> List[AIModelInfo]:
        """Dynamically discovers models available on the custom OpenAI-compatible server.
        
        When force_refresh=False, returns curated default without firing speculative network requests.
        When force_refresh=True, queries the custom endpoint /models path.
        """
        if self._discovered_models and not force_refresh:
            return list(self._discovered_models)

        # Do not fire speculative network requests during manifest inspection or startup
        if not force_refresh or not self.is_configured():
            return [
                AIModelInfo(
                    id=self.DEFAULT_MODEL,
                    name=f"Custom Model ({self._base_url})",
                    context_window=32768,
                    supports_formatting=True,
                    description="Custom endpoint model configured on your local or private server.",
                )
            ]

        try:
            data = self._http.request(
                method="GET",
                path="models",
                timeout=4.0,
                retries=0,
            )
            items = data.get("data", [])
            discovered: List[AIModelInfo] = []
            for item in items:
                m_id = item.get("id")
                if m_id:
                    discovered.append(
                        AIModelInfo(
                            id=m_id,
                            name=m_id,
                            context_window=item.get("context_window", 32768),
                            supports_formatting=True,
                            is_discovered=True,
                        )
                    )

            if discovered:
                self._discovered_models = discovered
                return list(discovered)
        except Exception as exc:
            logger.info(
                f"Custom endpoint model discovery at '{self._base_url}' was not reachable: {exc}. Using fallback default model."
            )

        return [
            AIModelInfo(
                id=self.DEFAULT_MODEL,
                name=f"Custom Model ({self._base_url})",
                context_window=32768,
                supports_formatting=True,
                description="Custom endpoint model configured on your local or private server.",
            )
        ]

    def validate_configuration(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> ProviderValidationResult:
        """Validates connection to the custom endpoint via a fast /models probe."""
        target_base = (base_url or self._base_url).strip().rstrip("/")
        target_key = api_key.strip() if api_key and api_key.strip() else self._api_key

        start = time.time()
        try:
            data = self._http.request(
                method="GET",
                path="models",
                override_base_url=target_base,
                override_key=target_key,
                timeout=6.0,
                retries=0,
            )
            count = len(data.get("data", []))
            latency = (time.time() - start) * 1000.0
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=True,
                message=f"Custom endpoint at '{target_base}' responded successfully.",
                latency_ms=round(latency, 1),
                discovered_models_count=count,
            )
        except Exception as exc:
            safe_msg = sanitize_credentials(str(exc), [target_key] if target_key else [])
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message=f"Custom endpoint validation at '{target_base}' failed: {safe_msg}",
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
        """Submits chat completion request to the custom endpoint."""
        if not self.is_enabled():
            raise ProviderDisabledError(
                message="Custom OpenAI-compatible provider is currently disabled.",
                provider=self.provider_id,
            )

        if not self.is_configured():
            raise ProviderConfigError(
                message="Custom provider base URL is missing.",
                code="CUSTOM_ENDPOINT_NOT_CONFIGURED",
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

        logger.info(f"Submitting request to Custom endpoint ({self._base_url}) [model: {target_model}]")

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
                message=f"Custom endpoint at '{self._base_url}' returned empty choices.",
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
