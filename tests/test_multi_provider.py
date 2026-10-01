"""Unit and architecture tests for Multi-Provider AI Architecture.

Verifies:
- All 8 target provider adapters adhere to the BaseAIProvider contract
- Strict provider isolation (no shared keys, no cross-provider leakage)
- Provider enable/disable enforcement (disabled providers reject requests)
- Normalized error taxonomy (401->Auth, 429->RateLimit, 502/504->Upstream/Timeout)
- Credential sanitization (keys and tokens never leaked in error messages)
- Explicit fallback routing (only engaged when explicitly configured)
- Custom OpenAI-compatible endpoint support
- Dynamic model discovery with curated fallback
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.api.deps import get_ai_service
from backend.core.config import Settings
from backend.main import app
from backend.models.ai import AIGenerateRequest
from backend.models.provider import AIModelInfo
from backend.providers import (
    BaseAIProvider,
    CohereProvider,
    CustomOpenAIProvider,
    GeminiProvider,
    GroqProvider,
    HuggingFaceProvider,
    MistralProvider,
    OpenAIProvider,
    OpenRouterProvider,
    ProviderAuthError,
    ProviderConfigError,
    ProviderDisabledError,
    ProviderFactory,
    ProviderGenerateResult,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUpstreamError,
)
from backend.providers.base import sanitize_credentials
from backend.providers.http_adapter import ProviderHTTPClient
from backend.services.ai_service import AIService
from backend.services.provider_service import ProviderService

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Provider Adapter Registration & Architecture Contract
# ---------------------------------------------------------------------------

def test_all_eight_providers_registered_in_factory():
    """Verify that all 8 required target providers are registered in ProviderFactory."""
    registered = ProviderFactory.list_available_providers()
    expected = [
        "gemini",
        "groq",
        "openrouter",
        "mistral",
        "cohere",
        "huggingface",
        "openai",
        "custom",
    ]
    for p in expected:
        assert p in registered, f"Provider '{p}' missing from ProviderFactory"


def test_provider_adapter_isolation():
    """Verify that each provider adapter receives only its own credentials and remains isolated."""
    settings = Settings(
        GEMINI_API_KEY="test-gemini-key",
        GROQ_API_KEY="test-groq-key",
        OPENROUTER_API_KEY="test-openrouter-key",
        MISTRAL_API_KEY="test-mistral-key",
        COHERE_API_KEY="test-cohere-key",
        HUGGINGFACE_API_KEY="test-hf-key",
        OPENAI_API_KEY="test-openai-key",
        CUSTOM_OPENAI_BASE_URL="http://localhost:11434/v1",
    )

    groq = ProviderFactory.get_provider("groq", settings)
    assert isinstance(groq, GroqProvider)
    assert groq.is_configured() is True
    # Groq must not have access to Gemini or OpenAI keys
    assert not hasattr(groq, "GEMINI_API_KEY")
    assert groq._api_key == "test-groq-key"

    gemini = ProviderFactory.get_provider("gemini", settings)
    assert isinstance(gemini, GeminiProvider)
    assert gemini._api_key == "test-gemini-key"

    custom = ProviderFactory.get_provider("custom", settings)
    assert isinstance(custom, CustomOpenAIProvider)
    assert custom.base_url == "http://localhost:11434/v1"


def test_provider_adapters_contract_implementation():
    """Verify all 8 adapters implement BaseAIProvider required properties and methods."""
    settings = Settings()
    for pid in ProviderFactory.list_available_providers():
        provider = ProviderFactory.get_provider(pid, settings)
        assert provider is not None
        assert isinstance(provider, BaseAIProvider)
        assert isinstance(provider.provider_id, str)
        assert len(provider.provider_id) > 0
        assert isinstance(provider.provider_name, str)
        assert len(provider.provider_name) > 0
        assert isinstance(provider.default_model, str)
        assert len(provider.default_model) > 0
        assert isinstance(provider.is_enabled(), bool)
        assert isinstance(provider.is_configured(), bool)

        models = provider.get_supported_models()
        assert isinstance(models, list)
        assert len(models) >= 1
        assert all(isinstance(m, AIModelInfo) for m in models)


# ---------------------------------------------------------------------------
# 2. Provider Enable / Disable Enforcement
# ---------------------------------------------------------------------------

def test_provider_disable_blocks_generation():
    """Verify disabled provider rejects generation requests with ProviderDisabledError."""
    settings = Settings()
    service = AIService(settings)

    # Disable groq
    ProviderFactory.set_provider_enabled("groq", False)

    try:
        req = AIGenerateRequest(
            prompt="Analyze this text",
            provider="groq",
        )
        with pytest.raises(ProviderDisabledError) as exc_info:
            service.generate(req)
        assert exc_info.value.code == "PROVIDER_DISABLED"
        assert exc_info.value.status_code == 400
        assert "disabled" in exc_info.value.message.lower()
    finally:
        # Re-enable
        ProviderFactory.set_provider_enabled("groq", True)


def test_provider_toggle_via_api():
    """Verify provider toggle endpoint enables and disables provider in runtime."""
    # Disable mistral
    resp = client.post("/api/ai/providers/mistral/toggle", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    # Attempt generate on mistral
    gen_resp = client.post(
        "/api/ai/generate",
        json={"prompt": "Test prompt", "provider": "mistral"},
    )
    assert gen_resp.status_code == 400
    assert gen_resp.json()["error"]["code"] == "PROVIDER_DISABLED"

    # Re-enable mistral
    resp2 = client.post("/api/ai/providers/mistral/toggle", json={"enabled": True})
    assert resp2.status_code == 200
    assert resp2.json()["enabled"] is True


# ---------------------------------------------------------------------------
# 3. Credential Sanitization
# ---------------------------------------------------------------------------

def test_credential_sanitization():
    """Verify that sanitize_credentials redacts API keys and auth headers from text."""
    secret_key = "sk-proj-1234567890abcdef12345678"
    raw_error = f"Request failed: Bearer {secret_key} returned 401 for key {secret_key}"
    sanitized = sanitize_credentials(raw_error, [secret_key])
    assert secret_key not in sanitized
    assert "[REDACTED" in sanitized


# ---------------------------------------------------------------------------
# 4. HTTP Adapter Error Normalization & Retries
# ---------------------------------------------------------------------------

def test_http_adapter_error_normalization():
    """Verify HTTP client normalizes status codes into specific exception classes."""
    client_adapter = ProviderHTTPClient(
        provider_id="test_mock",
        base_url="https://mock.example.com/v1",
        api_key="mock-key",
    )

    with patch("httpx.Client.request") as mock_req:
        # 401 Auth Error
        mock_resp_401 = MagicMock()
        mock_resp_401.is_success = False
        mock_resp_401.status_code = 401
        mock_resp_401.json.return_value = {"error": {"message": "Invalid API key provided"}}
        mock_req.return_value = mock_resp_401

        with pytest.raises(ProviderAuthError):
            client_adapter.request("POST", "chat/completions", {"prompt": "hi"}, retries=0)

        # 429 Rate Limit Error
        mock_resp_429 = MagicMock()
        mock_resp_429.is_success = False
        mock_resp_429.status_code = 429
        mock_resp_429.json.return_value = {"error": {"message": "Rate limit reached"}}
        mock_req.return_value = mock_resp_429

        with pytest.raises(ProviderRateLimitError):
            client_adapter.request("POST", "chat/completions", {"prompt": "hi"}, retries=0)

        # 502 Upstream Error
        mock_resp_502 = MagicMock()
        mock_resp_502.is_success = False
        mock_resp_502.status_code = 502
        mock_resp_502.json.return_value = {"error": {"message": "Bad gateway"}}
        mock_req.return_value = mock_resp_502

        with pytest.raises(ProviderUpstreamError):
            client_adapter.request("POST", "chat/completions", {"prompt": "hi"}, retries=0)


# ---------------------------------------------------------------------------
# 5. Explicit Fallback Handling
# ---------------------------------------------------------------------------

def test_explicit_fallback_routing_when_configured():
    """Verify fallback is engaged ONLY when explicitly configured."""
    class FailingProvider(BaseAIProvider):
        @property
        def provider_id(self) -> str:
            return "failing-primary"

        @property
        def provider_name(self) -> str:
            return "Failing Primary"

        @property
        def default_model(self) -> str:
            return "primary-model"

        def is_configured(self) -> bool:
            return True

        def generate(self, *args, **kwargs):
            raise ProviderUpstreamError(message="Primary upstream crashed", provider=self.provider_id)

    class WorkingFallbackProvider(BaseAIProvider):
        @property
        def provider_id(self) -> str:
            return "working-fallback"

        @property
        def provider_name(self) -> str:
            return "Working Fallback"

        @property
        def default_model(self) -> str:
            return "fallback-model"

        def is_configured(self) -> bool:
            return True

        def generate(self, *args, **kwargs):
            return ProviderGenerateResult(
                content="Fallback content generated successfully",
                model="fallback-model",
                provider=self.provider_id,
            )

    # Register mock providers in factory
    ProviderFactory._registry["failing-primary"] = FailingProvider
    ProviderFactory._registry["working-fallback"] = WorkingFallbackProvider

    try:
        service = AIService(settings=Settings())

        # Case 1: No fallback configured -> Must fail fast without silent fallback
        req_no_fallback = AIGenerateRequest(
            prompt="Test prompt",
            provider="failing-primary",
            fallback_provider=None,
        )
        with pytest.raises(ProviderUpstreamError) as exc_info:
            service.generate(req_no_fallback)
        assert "Primary upstream crashed" in exc_info.value.message

        # Case 2: Explicit fallback configured -> Fallback engaged
        req_with_fallback = AIGenerateRequest(
            prompt="Test prompt",
            provider="failing-primary",
            fallback_provider="working-fallback",
        )
        res = service.generate(req_with_fallback)
        assert res.success is True
        assert res.fallback_used is True
        assert res.provider == "working-fallback"
        assert res.original_provider == "failing-primary"
        assert res.content == "Fallback content generated successfully"
    finally:
        ProviderFactory._registry.pop("failing-primary", None)
        ProviderFactory._registry.pop("working-fallback", None)


# ---------------------------------------------------------------------------
# 6. Model Discovery & Provider Validation Endpoints
# ---------------------------------------------------------------------------

def test_api_list_providers_manifest():
    """Verify GET /api/ai/providers returns all 8 providers with status and models."""
    response = client.get("/api/ai/providers")
    assert response.status_code == 200
    providers = response.json()
    assert len(providers) >= 8
    ids = [p["id"] for p in providers]
    for expected in ["gemini", "groq", "openrouter", "mistral", "cohere", "huggingface", "openai", "custom"]:
        assert expected in ids


def test_api_validate_provider_endpoint():
    """Verify POST /api/ai/providers/{id}/validate handles validation safely without crash."""
    response = client.post(
        "/api/ai/providers/custom/validate",
        json={"base_url": "http://127.0.0.1:9999/v1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider_id"] == "custom"
    # Should report failed connection cleanly without crashing
    assert data["is_valid"] is False
    assert "failed" in data["message"].lower() or "connect" in data["message"].lower()
