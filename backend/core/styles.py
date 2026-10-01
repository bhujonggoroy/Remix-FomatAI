"""Centralized style configuration and typography presets for DOCX generation.

Defines all visual formatting, margins, font configurations, paragraph spacing,
line spacing, table styles, and headers/footers. Eliminates scattered formatting values.
"""

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class StylePresetName(str, Enum):
    """Supported formatting style preset identifiers."""
    ACADEMIC = "academic"
    RESEARCH_PAPER = "research_paper"
    EXAM = "exam"
    STUDY_NOTES = "study_notes"
    TEXTBOOK = "textbook"


class MarginsConfig(BaseModel):
    """Page margin dimensions in inches."""
    top_inches: float = 1.0
    bottom_inches: float = 1.0
    left_inches: float = 1.0
    right_inches: float = 1.0
    header_inches: float = 0.5
    footer_inches: float = 0.5


class FontConfig(BaseModel):
    """Font family configurations."""
    primary: str = "Times New Roman"
    heading: str = "Times New Roman"
    code: str = "Consolas"
    math: str = "Cambria Math"


class FontSizeConfig(BaseModel):
    """Font point sizes for document hierarchy."""
    title: float = 18.0
    subtitle: float = 14.0
    heading_1: float = 14.0
    heading_2: float = 13.0
    heading_3: float = 12.0
    body: float = 12.0
    abstract: float = 11.0
    table_cell: float = 10.5
    code_block: float = 9.5
    caption: float = 9.5
    header_footer: float = 9.0


class LineSpacingConfig(BaseModel):
    """Line spacing multipliers and paragraph spacing in points."""
    body_line_spacing: float = 2.0  # Double spacing (APA standard)
    body_space_after_pt: float = 0.0  # 0pt after when using indent
    body_first_line_indent_inches: float = 0.5  # Standard 0.5 in academic indent
    heading_1_before_pt: float = 12.0
    heading_1_after_pt: float = 6.0
    heading_2_before_pt: float = 10.0
    heading_2_after_pt: float = 4.0
    heading_3_before_pt: float = 8.0
    heading_3_after_pt: float = 2.0
    list_item_space_after_pt: float = 2.0
    table_cell_space_after_pt: float = 2.0
    code_line_spacing: float = 1.0
    code_space_before_pt: float = 6.0
    code_space_after_pt: float = 6.0


class ColorPalette(BaseModel):
    """Hex color definitions without '#' prefix for Word XML."""
    primary_text: str = "000000"
    heading_text: str = "000000"
    accent: str = "2A4B7C"
    muted: str = "555555"
    table_header_bg: str = "F2F2F2"
    table_header_text: str = "000000"
    table_border: str = "888888"
    code_bg: str = "F7F7F7"
    code_border: str = "E0E0E0"
    code_text: str = "222222"
    blockquote_border: str = "CCCCCC"


class HeaderFooterConfig(BaseModel):
    """Header and footer options."""
    show_header: bool = True
    show_footer: bool = True
    header_left: Optional[str] = None
    header_right: Optional[str] = "Running Head"
    footer_center: Optional[str] = None
    show_page_number_in_header: bool = False
    show_page_number_in_footer: bool = True
    first_page_different: bool = True


class DocumentStyleConfig(BaseModel):
    """Comprehensive style profile governing DOCX document generation."""
    preset_name: StylePresetName = StylePresetName.ACADEMIC
    display_name: str = "APA Academic Standard"
    description: str = "Double-spaced Times New Roman 12pt with 1-inch margins and running headers."
    fonts: FontConfig = Field(default_factory=FontConfig)
    sizes: FontSizeConfig = Field(default_factory=FontSizeConfig)
    margins: MarginsConfig = Field(default_factory=MarginsConfig)
    spacing: LineSpacingConfig = Field(default_factory=LineSpacingConfig)
    colors: ColorPalette = Field(default_factory=ColorPalette)
    header_footer: HeaderFooterConfig = Field(default_factory=HeaderFooterConfig)
    table_has_zebra_shading: bool = False
    table_header_bold: bool = True


# ---------------------------------------------------------------------------
# Centralized Preset Registry
# ---------------------------------------------------------------------------

PRESET_ACADEMIC = DocumentStyleConfig(
    preset_name=StylePresetName.ACADEMIC,
    display_name="Academic Standard (APA)",
    description="Formal APA 7th ed. format: Times New Roman 12pt, double spaced, 1-inch margins, 0.5in indent.",
    fonts=FontConfig(primary="Times New Roman", heading="Times New Roman", code="Consolas"),
    sizes=FontSizeConfig(
        title=18.0,
        heading_1=14.0,
        heading_2=13.0,
        heading_3=12.0,
        body=12.0,
        abstract=11.0,
        table_cell=10.5,
    ),
    margins=MarginsConfig(top_inches=1.0, bottom_inches=1.0, left_inches=1.0, right_inches=1.0),
    spacing=LineSpacingConfig(
        body_line_spacing=2.0,
        body_space_after_pt=0.0,
        body_first_line_indent_inches=0.5,
        heading_1_before_pt=18.0,
        heading_1_after_pt=6.0,
        heading_2_before_pt=12.0,
        heading_2_after_pt=4.0,
    ),
    colors=ColorPalette(
        primary_text="000000",
        heading_text="000000",
        table_header_bg="EAEAEA",
        table_border="666666",
    ),
    header_footer=HeaderFooterConfig(
        show_header=True,
        show_footer=True,
        header_right="Page ",
        show_page_number_in_header=False,
        show_page_number_in_footer=True,
        first_page_different=True,
    ),
)

PRESET_RESEARCH_PAPER = DocumentStyleConfig(
    preset_name=StylePresetName.RESEARCH_PAPER,
    display_name="Research Paper (IEEE / Nature)",
    description="Clean, compact research paper format: Times New Roman 11pt, 1.5 line spacing, structured headings.",
    fonts=FontConfig(primary="Times New Roman", heading="Times New Roman", code="Consolas"),
    sizes=FontSizeConfig(
        title=18.0,
        heading_1=13.5,
        heading_2=12.0,
        heading_3=11.0,
        body=11.0,
        abstract=10.0,
        table_cell=9.5,
    ),
    margins=MarginsConfig(top_inches=1.0, bottom_inches=1.0, left_inches=1.0, right_inches=1.0),
    spacing=LineSpacingConfig(
        body_line_spacing=1.5,
        body_space_after_pt=4.0,
        body_first_line_indent_inches=0.0,
        heading_1_before_pt=14.0,
        heading_1_after_pt=4.0,
        heading_2_before_pt=10.0,
        heading_2_after_pt=3.0,
    ),
    colors=ColorPalette(
        primary_text="111111",
        heading_text="1A365D",  # Navy accent for headings
        accent="2B6CB0",
        table_header_bg="F0F4F8",
        table_border="CBD5E0",
    ),
    header_footer=HeaderFooterConfig(
        show_header=True,
        show_footer=True,
        show_page_number_in_footer=True,
        first_page_different=True,
    ),
)

PRESET_EXAM = DocumentStyleConfig(
    preset_name=StylePresetName.EXAM,
    display_name="Examination / Assessment",
    description="High-clarity sans-serif format: Arial 10.5pt, compact spacing, clear section dividers.",
    fonts=FontConfig(primary="Arial", heading="Arial", code="Consolas"),
    sizes=FontSizeConfig(
        title=16.0,
        heading_1=13.0,
        heading_2=11.5,
        heading_3=10.5,
        body=10.5,
        table_cell=9.5,
    ),
    margins=MarginsConfig(top_inches=0.75, bottom_inches=0.75, left_inches=0.75, right_inches=0.75),
    spacing=LineSpacingConfig(
        body_line_spacing=1.15,
        body_space_after_pt=6.0,
        body_first_line_indent_inches=0.0,
        heading_1_before_pt=12.0,
        heading_1_after_pt=4.0,
    ),
    colors=ColorPalette(
        primary_text="000000",
        heading_text="000000",
        table_header_bg="F5F5F5",
        table_border="444444",
    ),
    header_footer=HeaderFooterConfig(
        show_header=True,
        show_footer=True,
        header_left="Examination Paper",
        show_page_number_in_footer=True,
        first_page_different=False,
    ),
)

PRESET_STUDY_NOTES = DocumentStyleConfig(
    preset_name=StylePresetName.STUDY_NOTES,
    display_name="Study Notes & Summaries",
    description="Modern readable study layout: Calibri 11pt, clean hierarchy with subtle slate styling.",
    fonts=FontConfig(primary="Calibri", heading="Calibri", code="Consolas"),
    sizes=FontSizeConfig(
        title=18.0,
        heading_1=14.0,
        heading_2=12.5,
        heading_3=11.0,
        body=11.0,
        table_cell=10.0,
    ),
    margins=MarginsConfig(top_inches=0.8, bottom_inches=0.8, left_inches=0.8, right_inches=0.8),
    spacing=LineSpacingConfig(
        body_line_spacing=1.2,
        body_space_after_pt=5.0,
        body_first_line_indent_inches=0.0,
        heading_1_before_pt=14.0,
        heading_1_after_pt=4.0,
    ),
    colors=ColorPalette(
        primary_text="1E293B",
        heading_text="312E81",  # Indigo
        accent="4F46E5",
        table_header_bg="EEF2FF",
        table_border="C7D2FE",
    ),
    header_footer=HeaderFooterConfig(
        show_header=True,
        show_footer=True,
        header_left="Study Notes",
        show_page_number_in_footer=True,
        first_page_different=False,
    ),
)

PRESET_TEXTBOOK = DocumentStyleConfig(
    preset_name=StylePresetName.TEXTBOOK,
    display_name="Textbook / Monograph",
    description="Elegant book typography: Georgia 10.5pt, generous leading, dignified classical headings.",
    fonts=FontConfig(primary="Georgia", heading="Georgia", code="Consolas"),
    sizes=FontSizeConfig(
        title=20.0,
        heading_1=15.0,
        heading_2=13.0,
        heading_3=11.5,
        body=10.5,
        table_cell=9.5,
    ),
    margins=MarginsConfig(top_inches=1.2, bottom_inches=1.2, left_inches=1.2, right_inches=1.2),
    spacing=LineSpacingConfig(
        body_line_spacing=1.25,
        body_space_after_pt=4.0,
        body_first_line_indent_inches=0.35,
        heading_1_before_pt=20.0,
        heading_1_after_pt=6.0,
    ),
    colors=ColorPalette(
        primary_text="18181B",
        heading_text="18181B",
        accent="713F12",
        table_header_bg="FAFAF9",
        table_border="A1A1AA",
    ),
    header_footer=HeaderFooterConfig(
        show_header=True,
        show_footer=True,
        show_page_number_in_footer=True,
        first_page_different=True,
    ),
)

STYLE_PRESETS: Dict[str, DocumentStyleConfig] = {
    StylePresetName.ACADEMIC.value: PRESET_ACADEMIC,
    StylePresetName.RESEARCH_PAPER.value: PRESET_RESEARCH_PAPER,
    StylePresetName.EXAM.value: PRESET_EXAM,
    StylePresetName.STUDY_NOTES.value: PRESET_STUDY_NOTES,
    StylePresetName.TEXTBOOK.value: PRESET_TEXTBOOK,
}


def get_style_preset(name: Optional[str]) -> DocumentStyleConfig:
    """Retrieves style configuration preset by key, falling back to ACADEMIC."""
    if not name:
        return PRESET_ACADEMIC
    key = name.lower().strip()
    return STYLE_PRESETS.get(key, PRESET_ACADEMIC)
