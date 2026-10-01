"""Unit tests for AI Generation API and Google Gemini Provider.

Verifies:
- Request validation (empty prompt, whitespace prompt)
- Missing API key handling (safe 503 error, no key leakage)
- Provider upstream error normalization
- Successful response using mocked provider behavior
Does NOT require a real API key for automated test execution.
"""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from google.genai.errors import APIError

from backend.api.deps import get_ai_service
from backend.core.config import Settings
from backend.main import app
from backend.models.ai import AIGenerateRequest
from backend.providers.base import (
    BaseAIProvider,
    ProviderConfigError,
    ProviderGenerateResult,
)
from backend.providers.gemini import GeminiProvider
from backend.services.ai_service import AIService

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Request Validation Tests
# ---------------------------------------------------------------------------

def test_request_validation_missing_prompt():
    """Verify that requests without a prompt return 422 Unprocessable Entity."""
    response = client.post("/api/ai/generate", json={})
    assert response.status_code == 422


def test_request_validation_empty_prompt():
    """Verify that empty prompt string is rejected."""
    response = client.post("/api/ai/generate", json={"prompt": ""})
    assert response.status_code == 422


def test_request_validation_whitespace_only_prompt():
    """Verify that whitespace-only prompt is rejected."""
    response = client.post("/api/ai/generate", json={"prompt": "   \n\t  "})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 2. Missing API Key Tests
# ---------------------------------------------------------------------------

def test_missing_api_key_returns_structured_error():
    """Verify missing GEMINI_API_KEY returns HTTP 503 with structured JSON error."""
    # Provide unconfigured AIService via dependency override to test unconfigured environment
    unconfigured_provider = GeminiProvider(api_key="")
    unconfigured_service = AIService(
        settings=Settings(GEMINI_API_KEY=None),
        provider=unconfigured_provider,
    )
    app.dependency_overrides[get_ai_service] = lambda: unconfigured_service

    try:
        response = client.post(
            "/api/ai/generate",
            json={"prompt": "Format this academic paper section."},
        )
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] in ("PROVIDER_NOT_CONFIGURED", "GEMINI_KEY_NOT_CONFIGURED")
        assert "not configured" in data["error"]["message"].lower()
        # Ensure no secrets or system paths leaked
        assert "password" not in response.text.lower()
        assert "secret" not in response.text.lower()
    finally:
        app.dependency_overrides.clear()


def test_gemini_provider_unconfigured_direct():
    """Verify GeminiProvider directly raises ProviderConfigError when unconfigured."""
    provider = GeminiProvider(api_key="")
    assert provider.is_configured() is False
    with pytest.raises(ProviderConfigError) as exc_info:
        provider.generate_text(prompt="Hello")
    assert exc_info.value.code == "GEMINI_KEY_NOT_CONFIGURED"


# ---------------------------------------------------------------------------
# 3. Provider Error Normalization Tests
# ---------------------------------------------------------------------------

def test_provider_upstream_error_normalization():
    """Verify upstream Gemini API errors are normalized into structured JSON with HTTP 502."""
    mock_client = MagicMock()
    # Simulate APIError from google-genai
    mock_client.models.generate_content.side_effect = APIError(
        502,
        {"error": {"message": "Simulated upstream quota / server fault"}},
    )

    provider = GeminiProvider(client=mock_client)
    service = AIService(settings=Settings(), provider=provider)

    app.dependency_overrides[get_ai_service] = lambda: service

    try:
        response = client.post(
            "/api/ai/generate",
            json={"prompt": "Analyze this introduction paragraph."},
        )
        assert response.status_code == 502
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "GEMINI_UPSTREAM_ERROR"
        assert "Simulated upstream quota" in data["error"]["message"]
    finally:
        app.dependency_overrides.clear()


def test_provider_rate_limit_error_normalization():
    """Verify rate limit (429) errors return HTTP 429 with RATE_LIMIT_EXCEEDED."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = APIError(
        429,
        {"error": {"message": "Resource has been exhausted"}},
    )

    provider = GeminiProvider(client=mock_client)
    service = AIService(settings=Settings(), provider=provider)

    app.dependency_overrides[get_ai_service] = lambda: service

    try:
        response = client.post(
            "/api/ai/generate",
            json={"prompt": "Summarize methodology."},
        )
        assert response.status_code == 429
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 4. Successful Response Using Mocked Provider Behavior
# ---------------------------------------------------------------------------

def test_successful_ai_generation_mocked_client():
    """Verify successful AI generation returns predictable structure without real API key."""
    # Mock genai.Client response structure
    mock_response = MagicMock()
    mock_response.text = "# Abstract\n\nThis study explores academic formatting automation."

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(client=mock_client)
    service = AIService(settings=Settings(), provider=provider)

    app.dependency_overrides[get_ai_service] = lambda: service

    try:
        response = client.post(
            "/api/ai/generate",
            json={
                "prompt": "Format the following abstract into APA style.",
                "model": "gemini-3.8-flash",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data == {
            "success": True,
            "provider": "gemini",
            "model": "gemini-3.8-flash",
            "content": "# Abstract\n\nThis study explores academic formatting automation.",
        }
        # Verify client called with exact parameters
        mock_client.models.generate_content.assert_called_once_with(
            model="gemini-3.8-flash",
            contents="Format the following abstract into APA style.",
        )
    finally:
        app.dependency_overrides.clear()


def test_gemini_provider_model_alias_resolution():
    """Verify deprecated model requests (e.g. gemini-2.5-flash) are automatically mapped to gemini-3.8-flash."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Normalized content"
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(client=mock_client)

    # Call with legacy model
    result = provider.generate_text(
        prompt="Test prompt",
        model="gemini-2.5-flash",
    )

    assert result.content == "Normalized content"
    assert result.model == "gemini-3.8-flash"
    mock_client.models.generate_content.assert_called_once_with(
        model="gemini-3.8-flash",
        contents="Test prompt",
    )


def test_ai_service_with_custom_provider_stub():
    """Verify AIService operates purely via the BaseAIProvider abstraction."""
    class MockCustomProvider(BaseAIProvider):
        @property
        def provider_id(self) -> str:
            return "mock-provider"

        @property
        def provider_name(self) -> str:
            return "Mock Provider"

        @property
        def default_model(self) -> str:
            return "mock-v1"

        def is_configured(self) -> bool:
            return True

        def get_supported_models(self):
            return []

        def generate_text(self, prompt: str, model=None, timeout=30.0):
            return ProviderGenerateResult(
                content=f"Processed: {prompt}",
                model=model or self.default_model,
                provider=self.provider_id,
            )

    service = AIService(settings=Settings(), provider=MockCustomProvider())
    req = AIGenerateRequest(prompt="Test abstract text")
    res = service.generate(req)
    assert res.success is True
    assert res.provider == "mock-provider"
    assert res.content == "Processed: Test abstract text"
