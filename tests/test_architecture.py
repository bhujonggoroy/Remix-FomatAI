"""Tests verifying backend architecture layers (Core, Services, Providers, Utils)."""

from backend.core.config import Settings, get_settings
from backend.models.health import HealthResponse, RootResponse
from backend.models.provider import AIModelInfo
from backend.providers.factory import ProviderFactory
from backend.providers.gemini import GeminiProvider
from backend.services.health_service import HealthService
from backend.services.provider_service import ProviderService
from backend.utils.text import count_words, sanitize_raw_text


def test_core_settings():
    """Verify settings loads properly and defaults are set safely."""
    settings = get_settings()
    assert settings.APP_NAME == "FormatAI"
    assert settings.FASTAPI_PORT == 8001
    assert settings.GEMINI_API_KEY is None or isinstance(settings.GEMINI_API_KEY, str)


def test_health_service_layer():
    """Verify HealthService business logic returns valid Pydantic models."""
    settings = Settings(APP_NAME="FormatAITest", APP_VERSION="1.0.0-test")
    service = HealthService(settings)

    health = service.get_health_status()
    assert isinstance(health, HealthResponse)
    assert health.status == "ok"
    assert health.service == "FormatAITest"
    assert health.backend == "python"

    root = service.get_root_status()
    assert isinstance(root, RootResponse)
    assert root.service == "FormatAITest"
    assert "FastAPI" in root.backend


def test_provider_layer_and_factory():
    """Verify provider factory and Gemini provider contract."""
    settings = Settings(GEMINI_API_KEY="")
    gemini = ProviderFactory.get_provider("gemini", settings)
    assert gemini is not None
    assert isinstance(gemini, GeminiProvider)
    assert gemini.provider_id == "gemini"
    assert gemini.provider_name == "Google Gemini"
    assert gemini.is_configured() is False

    models = gemini.get_supported_models()
    assert len(models) >= 2
    assert all(isinstance(m, AIModelInfo) for m in models)


def test_provider_service():
    """Verify ProviderService business logic querying provider discovery."""
    settings = Settings()
    service = ProviderService(settings)
    manifest = service.get_provider_manifest()
    assert len(manifest) >= 1
    gemini_info = next((p for p in manifest if p.id == "gemini"), None)
    assert gemini_info is not None
    assert gemini_info.name == "Google Gemini"


def test_utils_layer():
    """Verify text utility helpers."""
    assert count_words("FormatAI academic formatting engine") == 4
    assert count_words("") == 0
    assert sanitize_raw_text("  hello world  \r\n  second line  ") == "hello world\n  second line"
