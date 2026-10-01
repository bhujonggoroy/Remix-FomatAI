"""Data models for FormatAI Mathematics Processing Pipeline."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MathType(str, Enum):
    """Classification of mathematical expressions."""
    INLINE = "inline"
    DISPLAY = "display"


class MathSpan(BaseModel):
    """Represents a detected mathematical span within text."""
    start: int
    end: int
    raw_text: str
    latex: str
    math_type: MathType = MathType.INLINE
    confidence: float = 1.0


class TextSegment(BaseModel):
    """Represents a segmented portion of text, either plain prose or mathematics."""
    text: str
    is_math: bool = False
    math_type: Optional[MathType] = None
    latex: Optional[str] = None
    omml: Optional[str] = None


class MathConversionResult(BaseModel):
    """Outcome of converting a LaTeX expression to Word OMML representation."""
    latex: str
    is_display: bool = False
    success: bool
    omml: Optional[str] = None
    mathml: Optional[str] = None
    unicode_fallback: Optional[str] = None
    error_message: Optional[str] = None
