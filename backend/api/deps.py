"""FastAPI Dependency Injection helpers."""

from fastapi import Depends
from backend.core.config import Settings, get_settings
from backend.services.ai_service import AIService
from backend.services.content_cleanup_service import ContentCleanupService
from backend.services.document_service import DocumentService
from backend.services.docx_service import DocxService
from backend.services.formatting_service import FormattingService
from backend.services.health_service import HealthService
from backend.services.math_service import MathService
from backend.services.pdf_service import PdfService
from backend.services.provider_service import ProviderService


def get_health_service(settings: Settings = Depends(get_settings)) -> HealthService:
    """Dependency provider for HealthService."""
    return HealthService(settings)


def get_provider_service(settings: Settings = Depends(get_settings)) -> ProviderService:
    """Dependency provider for ProviderService."""
    return ProviderService(settings)


def get_ai_service(settings: Settings = Depends(get_settings)) -> AIService:
    """Dependency provider for AIService."""
    return AIService(settings)


def get_content_cleanup_service() -> ContentCleanupService:
    """Dependency provider for ContentCleanupService."""
    return ContentCleanupService()


def get_formatting_service() -> FormattingService:
    """Dependency provider for FormattingService."""
    return FormattingService()


def get_document_service(
    settings: Settings = Depends(get_settings),
    cleanup_service: ContentCleanupService = Depends(get_content_cleanup_service),
    formatting_service: FormattingService = Depends(get_formatting_service),
) -> DocumentService:
    """Dependency provider for DocumentService orchestrator."""
    return DocumentService(
        settings=settings,
        content_cleanup_service=cleanup_service,
        formatting_service=formatting_service,
    )


def get_math_service() -> MathService:
    """Dependency provider for MathService."""
    return MathService()


def get_docx_service(
    math_service: MathService = Depends(get_math_service),
) -> DocxService:
    """Dependency provider for DocxService."""
    return DocxService(math_service=math_service)


def get_pdf_service(
    math_service: MathService = Depends(get_math_service),
) -> PdfService:
    """Dependency provider for PdfService."""
    return PdfService(math_service=math_service)

