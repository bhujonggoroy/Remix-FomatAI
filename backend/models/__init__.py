"""FormatAI Data Models Package.
Contains Pydantic request/response schemas and domain data contracts.
"""
from backend.models.health import HealthResponse, RootResponse
from backend.models.provider import AIModelInfo, AIProviderInfo
from backend.models.ai import (
    AIGenerateRequest,
    AIGenerateResponse,
    AIErrorDetail,
    AIErrorResponse,
)
from backend.models.document import (
    DocumentElementType,
    EntityType,
    InlineEntity,
    TableData,
    TableColumnAlign,
    DocumentElement,
    DocumentStats,
    DocumentAnalysis,
    DocumentStructure,
    DocumentProcessingOptions,
    DocumentProcessRequest,
    DocumentProcessResponse,
    DocumentDocxExportRequest,
)
from backend.models.math import (
    MathType,
    MathSpan,
    TextSegment,
    MathConversionResult,
)

__all__ = [
    "HealthResponse",
    "RootResponse",
    "AIModelInfo",
    "AIProviderInfo",
    "AIGenerateRequest",
    "AIGenerateResponse",
    "AIErrorDetail",
    "AIErrorResponse",
    "DocumentElementType",
    "EntityType",
    "InlineEntity",
    "TableData",
    "TableColumnAlign",
    "DocumentElement",
    "DocumentStats",
    "DocumentAnalysis",
    "DocumentStructure",
    "DocumentProcessingOptions",
    "DocumentProcessRequest",
    "DocumentProcessResponse",
    "DocumentDocxExportRequest",
    "MathType",
    "MathSpan",
    "TextSegment",
    "MathConversionResult",
]
