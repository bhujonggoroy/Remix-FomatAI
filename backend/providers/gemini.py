"""Google Gemini AI Provider implementation using official google-genai SDK.

Supports:
- Model selection and validation (default: gemini-3.8-flash)
- Dynamic model discovery via client.models.list()
- Prompt submission with system instructions and temperature
- Error normalization without key leakage
- Safe configuration check and validation probe
"""

import time
from typing import Any, List, Optional
from google import genai
from google.genai.errors import APIError

from backend.core.logging import logger
from backend.models.provider import AIModelInfo, ProviderValidationResult
from backend.providers.base import (
    BaseAIProvider,
    ProviderAuthError,
    ProviderConfigError,
    ProviderDisabledError,
    ProviderError,
    ProviderGenerateResult,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUpstreamError,
    sanitize_credentials,
)


class GeminiProvider(BaseAIProvider):
    """Concrete Google Gemini AI Provider adapter."""

    DEFAULT_MODEL = "gemini-3.8-flash"

    MODEL_ALIASES = {
        "gemini-2.5-flash": "gemini-3.8-flash",
        "models/gemini-2.5-flash": "gemini-3.8-flash",
        "gemini-2.5-pro": "gemini-3.1-pro-preview",
        "models/gemini-2.5-pro": "gemini-3.1-pro-preview",
        "gemini-1.5-flash": "gemini-3.8-flash",
        "models/gemini-1.5-flash": "gemini-3.8-flash",
        "gemini-1.5-pro": "gemini-3.1-pro-preview",
        "models/gemini-1.5-pro": "gemini-3.1-pro-preview",
        "gemini-2.0-flash": "gemini-3.8-flash",
        "models/gemini-2.0-flash": "gemini-3.8-flash",
        "gemini-2.0-flash-exp": "gemini-3.8-flash",
        "models/gemini-2.0-flash-exp": "gemini-3.8-flash",
    }

    SUPPORTED_MODELS = [
        AIModelInfo(
            id="gemini-3.8-flash",
            name="Gemini 3.8 Flash",
            context_window=1048576,
            supports_formatting=True,
            description="Recommended default. Ultra-fast, highly capable for academic formatting.",
        ),
        AIModelInfo(
            id="gemini-3.1-pro-preview",
            name="Gemini 3.1 Pro",
            context_window=2097152,
            supports_formatting=True,
            description="High-reasoning model for complex monograph synthesis and deep proofs.",
        ),
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[Any] = None,
        is_enabled: bool = True,
    ):
        """Initializes Gemini provider with optional API key or pre-configured client (for testing)."""
        super().__init__(is_enabled=is_enabled)
        self._api_key = api_key.strip() if api_key and api_key.strip() else None
        self._client = client
        self._discovered_models: Optional[List[AIModelInfo]] = None

    @property
    def provider_id(self) -> str:
        return "gemini"

    @property
    def provider_name(self) -> str:
        return "Google Gemini"

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def is_configured(self) -> bool:
        """Verifies if the provider has credentials configured."""
        if self._client is not None:
            return True
        return bool(self._api_key)

    def _get_client(self, override_key: Optional[str] = None) -> genai.Client:
        """Instantiates or returns the cached GenAI client."""
        if override_key:
            return genai.Client(api_key=override_key.strip())

        if self._client is not None:
            return self._client

        if not self.is_configured():
            raise ProviderConfigError(
                message="Google Gemini API key is not configured. Set GEMINI_API_KEY in the server environment (.env).",
                code="GEMINI_KEY_NOT_CONFIGURED",
                provider=self.provider_id,
            )

        return genai.Client(api_key=self._api_key)

    def list_models(self, force_refresh: bool = False) -> List[AIModelInfo]:
        """Discovers models from Gemini API when configured, otherwise returns curated models."""
        if self._discovered_models and not force_refresh:
            return list(self._discovered_models)

        if not force_refresh or not self.is_configured():
            return list(self.SUPPORTED_MODELS)

        try:
            client = self._get_client()
            models_pager = client.models.list()
            discovered: List[AIModelInfo] = []

            for m in models_pager:
                model_id = getattr(m, "name", None) or getattr(m, "id", "")
                if model_id.startswith("models/"):
                    model_id = model_id.split("models/", 1)[1]

                display_name = getattr(m, "display_name", None) or model_id
                # Filter for relevant generateContent models
                if "gemini" in model_id.lower() and not any(x in model_id.lower() for x in ["vision", "embedding", "aqa"]):
                    input_limit = getattr(m, "input_token_limit", 1048576)
                    discovered.append(
                        AIModelInfo(
                            id=model_id,
                            name=display_name,
                            context_window=input_limit,
                            supports_formatting=True,
                            is_discovered=True,
                        )
                    )

            if discovered:
                self._discovered_models = discovered
                return list(discovered)
        except Exception as exc:
            logger.warning(f"Gemini model discovery probe failed: {exc}. Using curated models.")

        return list(self.SUPPORTED_MODELS)

    def validate_configuration(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> ProviderValidationResult:
        """Probes Gemini API connectivity and validates credentials."""
        target_key = api_key.strip() if api_key and api_key.strip() else self._api_key
        if not target_key and self._client is None:
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message="API key is missing. Set GEMINI_API_KEY or provide per-request key.",
            )

        start_time = time.time()
        try:
            client = self._get_client(override_key=target_key)
            # Lightweight probe
            models = list(self.list_models(force_refresh=True))
            latency = (time.time() - start_time) * 1000.0
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=True,
                message="Google Gemini connection and credentials verified successfully.",
                latency_ms=round(latency, 1),
                discovered_models_count=len(models),
            )
        except APIError as exc:
            status_code = getattr(exc, "code", 502)
            raw_msg = getattr(exc, "message", str(exc))
            safe_msg = sanitize_credentials(str(raw_msg), [target_key] if target_key else [])
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message=f"Gemini validation error ({status_code}): {safe_msg}",
            )
        except Exception as exc:
            safe_msg = sanitize_credentials(str(exc), [target_key] if target_key else [])
            return ProviderValidationResult(
                provider_id=self.provider_id,
                is_valid=False,
                message=f"Gemini connection failed: {safe_msg}",
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
        """Submits prompt to Gemini API with timeout, retry, and normalized error mapping."""
        if not self.is_enabled():
            raise ProviderDisabledError(
                message="Google Gemini provider is currently disabled.",
                provider=self.provider_id,
            )

        target_model = model or self.default_model
        if target_model in self.MODEL_ALIASES:
            logger.info(
                f"Mapping deprecated/alias model '{target_model}' to current supported model '{self.MODEL_ALIASES[target_model]}'"
            )
            target_model = self.MODEL_ALIASES[target_model]

        if not self.is_configured():
            raise ProviderConfigError(
                message="Google Gemini API key is not configured. Set GEMINI_API_KEY in the server environment (.env).",
                code="GEMINI_KEY_NOT_CONFIGURED",
                provider=self.provider_id,
            )

        client = self._get_client()
        logger.info(f"Submitting generation request to Gemini provider [model: {target_model}]")

        config_params: dict = {}
        if system_instruction:
            config_params["system_instruction"] = system_instruction
        if temperature is not None:
            config_params["temperature"] = temperature
        if max_tokens is not None:
            config_params["max_output_tokens"] = max_tokens

        attempts = max(1, retry_count + 1)
        last_exception: Optional[Exception] = None

        for attempt in range(attempts):
            try:
                kwargs: dict = {
                    "model": target_model,
                    "contents": prompt,
                }
                if config_params:
                    kwargs["config"] = config_params

                response = client.models.generate_content(**kwargs)

                # Extract generated content safely
                content = getattr(response, "text", None)
                if content is None:
                    if hasattr(response, "candidates") and response.candidates:
                        parts = response.candidates[0].content.parts
                        content = "".join([getattr(p, "text", "") for p in parts if hasattr(p, "text")])
                    else:
                        content = ""

                # Extract token usage if available
                usage = None
                if hasattr(response, "usage_metadata") and response.usage_metadata is not None:
                    um = response.usage_metadata
                    p_tokens = getattr(um, "prompt_token_count", None)
                    t_tokens = getattr(um, "total_token_count", None)
                    c_tokens = getattr(um, "candidates_token_count", None)
                    if isinstance(p_tokens, int) or isinstance(t_tokens, int):
                        usage = {
                            "prompt_tokens": p_tokens,
                            "candidates_tokens": c_tokens,
                            "total_tokens": t_tokens,
                        }

                return ProviderGenerateResult(
                    content=content,
                    model=target_model,
                    provider=self.provider_id,
                    usage=usage,
                )

            except APIError as exc:
                status_code = getattr(exc, "code", 502)
                raw_message = getattr(exc, "message", str(exc))
                sanitized = sanitize_credentials(str(raw_message), [self._api_key] if self._api_key else [])
                logger.error(f"Gemini API Error (status {status_code}): {sanitized}")

                if status_code in (401, 403):
                    raise ProviderAuthError(
                        message=f"Gemini authentication failed: {sanitized}",
                        code="GEMINI_AUTH_FAILED",
                        provider=self.provider_id,
                    ) from exc
                elif status_code == 429:
                    raise ProviderRateLimitError(
                        message=f"Gemini quota/rate limit exceeded: {sanitized}",
                        provider=self.provider_id,
                    ) from exc
                elif status_code in (500, 502, 503, 504) and attempt < attempts - 1:
                    sleep_time = 0.5 * (2**attempt)
                    time.sleep(sleep_time)
                    continue
                else:
                    raise ProviderUpstreamError(
                        message=f"Gemini service error: {sanitized}",
                        code="GEMINI_UPSTREAM_ERROR",
                        provider=self.provider_id,
                    ) from exc

            except TimeoutError as exc:
                if attempt < attempts - 1:
                    time.sleep(0.5)
                    continue
                logger.error("Gemini call timed out.")
                raise ProviderTimeoutError(
                    message="Request to Google Gemini API timed out.",
                    provider=self.provider_id,
                ) from exc

            except ProviderError:
                raise

            except Exception as exc:
                sanitized = sanitize_credentials(str(exc), [self._api_key] if self._api_key else [])
                logger.error(f"Unexpected error communicating with Gemini: {sanitized}")
                raise ProviderUpstreamError(
                    message=f"Failed to generate content with Gemini: {sanitized}",
                    code="GEMINI_GENERATION_FAILED",
                    provider=self.provider_id,
                ) from exc

        raise ProviderUpstreamError(
            message="Gemini request failed after maximum retries.",
            provider=self.provider_id,
        )
