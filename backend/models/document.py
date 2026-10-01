"""Internal structured academic document models for FormatAI.

Defines the complete domain model for parsed, cleaned, and structured academic documents.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentElementType(str, Enum):
    """Supported academic document element classifications."""
    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    ORDERED_LIST = "ordered_list"
    UNORDERED_LIST = "unordered_list"
    TABLE = "table"
    BLOCKQUOTE = "blockquote"
    CODE_BLOCK = "code_block"
    MATH_BLOCK = "math_block"
    CITATION = "citation"
    REFERENCE_ITEM = "reference_item"
    REFERENCE_LIST = "reference_list"
    ABSTRACT = "abstract"
    METADATA = "metadata"


class EntityType(str, Enum):
    """Fine-grained inline semantic entities."""
    INLINE_MATH = "inline_math"
    DISPLAY_MATH = "display_math"
    SCIENTIFIC_NOTATION = "scientific_notation"
    CHEMICAL_FORMULA = "chemical_formula"
    CITATION_REFERENCE = "citation_reference"
    BOLD = "bold"
    ITALIC = "italic"
    CODE_INLINE = "code_inline"


class InlineEntity(BaseModel):
    """An inline academic entity detected within text."""
    entity_type: EntityType
    raw_text: str
    normalized_text: str
    start: int
    end: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TableColumnAlign(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class TableData(BaseModel):
    """Structured table representation."""
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)
    alignments: List[TableColumnAlign] = Field(default_factory=list)
    caption: Optional[str] = None


class DocumentElement(BaseModel):
    """A discrete structural element within the academic document."""
    id: str = Field(..., description="Unique element identifier")
    type: DocumentElementType
    content: str = Field(default="", description="Normalized text content")
    raw_content: str = Field(default="", description="Original unparsed text slice")
    level: Optional[int] = Field(default=None, description="Heading level (1-6) or list nesting depth")
    items: Optional[List[str]] = Field(default=None, description="List item entries")
    table_data: Optional[TableData] = Field(default=None, description="Parsed tabular structure")
    language: Optional[str] = Field(default=None, description="Programming/markup language for code blocks")
    math_syntax: Optional[str] = Field(default=None, description="e.g. 'latex', 'asciimath'")
    entities: List[InlineEntity] = Field(default_factory=list, description="Extracted inline entities")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags")


class DocumentStats(BaseModel):
    """Computed structural metrics."""
    word_count: int = 0
    character_count: int = 0
    reading_time_minutes: float = 0.0
    paragraph_count: int = 0
    heading_count: int = 0
    table_count: int = 0
    math_block_count: int = 0
    citation_count: int = 0
    reference_count: int = 0


class DocumentAnalysis(BaseModel):
    """Diagnostics and quality report from content analysis."""
    detected_title: Optional[str] = None
    has_abstract: bool = False
    has_references: bool = False
    detected_style_candidate: Optional[str] = "APA"  # e.g. APA, IEEE, MLA, Harvard
    heading_hierarchy_valid: bool = True
    hierarchy_issues: List[str] = Field(default_factory=list)
    math_density: float = 0.0
    structure_quality_score: float = 100.0
    detected_entities_summary: Dict[str, int] = Field(default_factory=dict)
    diagnostics: List[str] = Field(default_factory=list)


class DocumentStructure(BaseModel):
    """Full internal document representation model."""
    title: Optional[str] = None
    abstract: Optional[str] = None
    elements: List[DocumentElement] = Field(default_factory=list)
    stats: DocumentStats = Field(default_factory=DocumentStats)
    references: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentProcessingOptions(BaseModel):
    """Configuration toggles for the processing pipeline."""
    enable_content_cleanup: bool = Field(default=True, description="Remove AI prefixes, conversational noise, orphan bullets")
    enable_formatting_cleanup: bool = Field(default=True, description="Fix heading hierarchy, list formatting, typography")
    target_style: str = Field(default="APA", description="Academic styling profile (APA, IEEE, Harvard, MLA)")
    smart_typography: bool = Field(default=True, description="Convert quotes, em-dashes, ellipses")
    enabled_skills: Optional[List[str]] = Field(default=None, description="Explicit list of skills to execute")
    disabled_skills: Optional[List[str]] = Field(default=None, description="Skills explicitly disabled by user")


class DocumentProcessRequest(BaseModel):
    """Request payload for processing academic documents."""
    raw_text: str = Field(..., min_length=1, description="Raw academic content to parse and structure")
    options: DocumentProcessingOptions = Field(default_factory=DocumentProcessingOptions)


class DocumentProcessResponse(BaseModel):
    """Full response containing the internal document model, analysis, and pipeline metrics."""
    success: bool = True
    document: DocumentStructure
    analysis: DocumentAnalysis
    executed_skills: List[str] = Field(default_factory=list, description="Skills that processed the document")
    skipped_skills: List[str] = Field(default_factory=list, description="Skills that were disabled or skipped")
    pipeline_stages: Dict[str, Any] = Field(default_factory=dict)


class DocumentDocxExportRequest(BaseModel):
    """Request payload for exporting to Microsoft Word .docx format."""
    document: Optional[DocumentStructure] = Field(
        default=None,
        description="Structured document representation. If omitted, raw_text is processed first.",
    )
    raw_text: Optional[str] = Field(
        default=None,
        description="Raw academic text to format and export if document is not provided.",
    )
    preset: str = Field(
        default="academic",
        description="Style preset name: academic, research_paper, exam, study_notes, textbook",
    )
    filename: Optional[str] = Field(
        default=None,
        description="Optional custom file name without extension",
    )
    options: DocumentProcessingOptions = Field(default_factory=DocumentProcessingOptions)


class DocumentPdfExportRequest(BaseModel):
    """Request payload for exporting to Adobe PDF format."""
    document: Optional[DocumentStructure] = Field(
        default=None,
        description="Structured document representation. If omitted, raw_text is processed first.",
    )
    raw_text: Optional[str] = Field(
        default=None,
        description="Raw academic text to format and export if document is not provided.",
    )
    preset: str = Field(
        default="academic",
        description="Style preset name: academic, research_paper, exam, study_notes, textbook",
    )
    filename: Optional[str] = Field(
        default=None,
        description="Optional custom file name without extension",
    )
    options: DocumentProcessingOptions = Field(default_factory=DocumentProcessingOptions)
