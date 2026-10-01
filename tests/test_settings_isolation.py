"""Backend Automated Tests for User Settings Isolation and Statelessness.

Verifies:
1. Backend is strictly stateless regarding user settings and credentials
2. User A's per-request API key is NOT stored or leaked to User B
3. User A's per-request custom base_url is NOT retained for User B
4. Backend provider endpoints never return user credentials or private settings
5. Error responses strictly redact secret API keys
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.core.config import Settings
from backend.main import app
from backend.models.ai import AIGenerateRequest
from backend.providers.base import sanitize_credentials
from backend.providers.factory import ProviderFactory
from backend.services.ai_service import AIService

client = TestClient(app)


def test_backend_has_no_shared_user_settings_endpoints():
    """Verify backend has no endpoints storing or returning user settings."""
    # Ensure standard REST routes for user settings do NOT exist on server
    resp = client.get("/api/users/settings")
    assert resp.status_code == 404

    resp = client.get("/api/user/settings")
    assert resp.status_code == 404

    resp = client.post("/api/user/settings", json={"api_key": "secret"})
    assert resp.status_code == 404


def test_user_a_key_does_not_leak_to_user_b():
    """Verify User A's per-request API key does not persist into User B's request."""
    settings = Settings(
        GROQ_API_KEY=None,  # No server-level fallback key
    )
    service = AIService(settings)

    user_a_key = "gsk_user_a_private_key_1111111111111111"

    # User A submits request with personal key
    with patch("httpx.Client.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "User A output"}}]
        }
        mock_req.return_value = mock_resp

        req_a = AIGenerateRequest(
            prompt="Hello from User A",
            provider="groq",
            api_key=user_a_key,
        )
        res_a = service.generate(req_a)
        assert res_a.content == "User A output"

        # Verify User A's key was sent in the authorization header
        auth_call_a = mock_req.call_args[1]["headers"]["Authorization"]
        assert user_a_key in auth_call_a

    # User B now submits request WITHOUT an API key
    # Must fail because User A's key must NOT have persisted on the server
    req_b = AIGenerateRequest(
        prompt="Hello from User B",
        provider="groq",
        api_key=None,
    )
    with pytest.raises(Exception) as exc_info:
        service.generate(req_b)

    # Groq provider should report not configured because no key exists for User B
    assert "not configured" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower()


def test_user_a_custom_endpoint_does_not_leak_to_user_b():
    """Verify User A's custom base_url override is ephemeral and not retained for User B."""
    settings = Settings()
    service = AIService(settings)

    user_a_endpoint = "http://user-a-private-ollama.internal:11434/v1"

    with patch("httpx.Client.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Custom model output"}}]
        }
        mock_req.return_value = mock_resp

        req_a = AIGenerateRequest(
            prompt="Generate text",
            provider="custom",
            base_url=user_a_endpoint,
        )
        res_a = service.generate(req_a)
        assert res_a.content == "Custom model output"

        # Check call URL used User A's endpoint
        call_url_a = mock_req.call_args.kwargs.get("url") or str(mock_req.call_args)
        assert "user-a-private-ollama.internal" in call_url_a

    # User B sends request to custom provider without override
    # Must use system default base_url, NOT User A's endpoint
    custom_prov = ProviderFactory.get_provider("custom", settings)
    assert custom_prov is not None
    assert "user-a-private-ollama.internal" not in custom_prov.base_url


def test_providers_endpoint_never_exposes_user_keys():
    """Verify GET /api/ai/providers response contains NO user credentials."""
    resp = client.get("/api/ai/providers")
    assert resp.status_code == 200
    providers = resp.json()
    for prov in providers:
        assert "api_key" not in prov
        assert "secret" not in prov
        assert "token" not in prov
        assert "user" not in prov


def test_error_redaction_prevents_credential_leakage():
    """Verify that credentials in exceptions are redacted and never returned to the client."""
    secret_key = "gsk_super_secret_user_token_99999"
    raw_error = f"HTTP 401 Unauthorized for Bearer {secret_key}"
    sanitized = sanitize_credentials(raw_error, [secret_key])

    assert secret_key not in sanitized
    assert "[REDACTED" in sanitized
