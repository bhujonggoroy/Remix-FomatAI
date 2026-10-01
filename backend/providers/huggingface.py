"""Hugging Face AI Provider adapter implementation.

Supports open models (Qwen, Llama, Mistral, Gemma) hosted on Hugging Face Serverless / Inference endpoints.
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


class HuggingFaceProvider(BaseAIProvider):
    """Adapter for Hugging Face Inference API / Router endpoints."""

    DEFAULT_MODEL = "Qwen/Qwen2.5-72B-Instruct"
    BASE_URL = "https://router.huggingface.co/v1"

    SUPPORTED_MODELS = [
        AIModelInfo(
            id="Qwen/Qwen2.5-72B-Instruct",
            name="Qwen 2.5 72B Instruct",
            context_window=131072,
            supports_formatting=True,
            description="Leaderboard top-ranking open model with strong mathematical and LaTeX typesetting precision.",
        ),
        AIModelInfo(
            id="meta-llama/Llama-3.3-70B-Instruct",
            name="Meta Llama 3.3 70B",
            context_window=131072,
            supports_formatting=True,
            description="High-fidelity reasoning engine for academic manuscripts.",
        ),
        AIModelInfo(
            id="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
            name="DeepSeek R1 Distill Qwen 32B",
            context_window=64000,
            supports_formatting=True,
            description="Specialized math and reasoning distillation.",
        ),
        AIModelInfo(
            id="mistralai/Mistral-7B-Instruct-v0.3",
            name="Mistral 7B Instruct v0.3",
            context_window=32768,
            supports_formatting=True,
            description="Compact, highly responsive open model.",
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
            provider_id="huggingface",
            base_url=self.BASE_URL,
            api_key=self._api_key,
        )
        self._discovered_models: Optional[List[AIModelInfo]] = None

    @property
    def provider_id(self) -> str:
        return "huggingface"

    @property
    def provider_name(self) -> str:
        return "Hugging Face"

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def list_models(self, force_refresh: bool = False) -> List[AIModelInfo]:
        """Returns curated Hugging Face models optimized for academic formatting."""
        return list(self.SUPPORTED_MODELS)

    def validate_configuration(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> ProviderValidationResult:
        """Validates Hugging Face token by checking whoami endpoint."""
        target_key = api_key.strip() if api_key and api_key.strip() else self._api_key
        if not target_key:
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message="Hugging Face API token is missing. Set HUGGINGFACE_API_KEY / HF_TOKEN in server environment or provide per-request key.",
            )

        start = time.time()
        try:
            # Probe whoami endpoint
            client = ProviderHTTPClient(
                provider_id="huggingface",
                base_url="https://huggingface.co/api",
                api_key=target_key,
            )
            data = client.request(
                method="GET",
                path="whoami-v2",
                timeout=6.0,
                retries=0,
            )
            username = data.get("name", "Authenticated User")
            latency = (time.time() - start) * 1000.0
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=True,
                message=f"Hugging Face token verified for account '{username}'.",
                latency_ms=round(latency, 1),
                discovered_models_count=len(self.SUPPORTED_MODELS),
            )
        except Exception as exc:
            safe_msg = sanitize_credentials(str(exc), [target_key] if target_key else [])
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message=f"Hugging Face validation failed: {safe_msg}",
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
        """Submits generation request to Hugging Face router chat completions."""
        if not self.is_enabled():
            raise ProviderDisabledError(
                message="Hugging Face provider is currently disabled.",
                provider=self.provider_id,
            )

        if not self.is_configured():
            raise ProviderConfigError(
                message="Hugging Face API token is not configured. Set HUGGINGFACE_API_KEY in the server environment (.env).",
                code="HUGGINGFACE_KEY_NOT_CONFIGURED",
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

        logger.info(f"Submitting request to Hugging Face [model: {target_model}]")

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
                message="Hugging Face returned empty completion choices.",
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
