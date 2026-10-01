"""Professional PDF Generation Engine for FormatAI.

Consumes the internal FormatAI DocumentStructure model and produces publication-grade
PDF documents using ReportLab and centralized style presets (styles.py).

Features supported:
- Full document structure: Title, Heading 1, Heading 2, Heading 3, Paragraphs, Abstract
- Preserves typography, margins, and line spacing from centralized presets (APA, Research Paper, Exam, Study Notes, Textbook)
- Rich inline formatting: Bold, Italic, Underline, Inline Code, Inline Math, Citations
- Academic tabular data: Proportional column widths, shaded header rows, borders, text wrapping
- Numbered and bulleted lists with hanging indents
- Academic blockquotes and quotations with indentation
- Math blocks and LaTeX representations rendered into clean Unicode/rich text
- Monospaced code blocks with background shading
- Dynamic page numbering ("Page X of Y") and running headers via NumberedCanvas
- Strict page-flow protection: keepWithNext on headings, zero accidental blank pages, no duplicate content
"""

import html
import io
import re
from typing import Any, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.core.logging import logger
from backend.core.styles import (
    DocumentStyleConfig,
    StylePresetName,
    get_style_preset,
)
from backend.models.document import (
    DocumentElement,
    DocumentElementType,
    DocumentStructure,
    TableColumnAlign,
    TableData,
)
from backend.models.math import MathType
from backend.services.math_service import MathService


class NumberedCanvas(canvas.Canvas):
    """Two-pass ReportLab Canvas that computes total page count dynamically.

    Renders running headers and footers with accurate 'Page X of Y' pagination
    without inserting blank pages or overflowing margins.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[dict] = []
        self.doc_title: str = "Academic Document"
        self.header_right: Optional[str] = "Running Head"
        self.header_left: Optional[str] = None
        self.footer_center: Optional[str] = None
        self.show_header: bool = True
        self.show_footer: bool = True
        self.first_page_different: bool = True
        self.margin_left: float = 72.0
        self.margin_right: float = 72.0
        self.margin_top: float = 72.0
        self.margin_bottom: float = 72.0
        self.page_width: float = 612.0
        self.page_height: float = 792.0
        self.primary_font: str = "Times-Roman"

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_decorations(self, total_pages: int) -> None:
        is_first_page = (self._pageNumber == 1)
        self.saveState()
        self.setFont(self.primary_font, 9)
        self.setFillColor(colors.HexColor("#555555"))

        # 1. Running Header (Skip on first page if first_page_different is enabled)
        if self.show_header and not (is_first_page and self.first_page_different):
            header_y = self.page_height - (self.margin_top * 0.55)
            left_text = self.header_left or (self.doc_title[:45] + "..." if len(self.doc_title) > 45 else self.doc_title)
            self.drawString(self.margin_left, header_y, left_text)

            right_text = self.header_right or ""
            if right_text:
                self.drawRightString(self.page_width - self.margin_right, header_y, right_text)

            # Subtle hairline rule below header
            self.setStrokeColor(colors.HexColor("#DDDDDD"))
            self.setLineWidth(0.5)
            self.line(self.margin_left, header_y - 4, self.page_width - self.margin_right, header_y - 4)

        # 2. Running Footer (Page numbering)
        if self.show_footer:
            footer_y = self.margin_bottom * 0.45
            page_text = f"Page {self._pageNumber} of {total_pages}"
            if self.footer_center:
                page_text = f"{self.footer_center} | {page_text}"

            self.drawCentredString(self.page_width / 2.0, footer_y, page_text)

        self.restoreState()


class PdfService:
    """Orchestrates publication-grade PDF document compilation from DocumentStructure."""

    def __init__(
        self,
        style_config: Optional[DocumentStyleConfig] = None,
        math_service: Optional[MathService] = None,
    ):
        self._style_config = style_config or get_style_preset(StylePresetName.ACADEMIC.value)
        self._math_service = math_service or MathService()

    def generate_pdf(
        self,
        document: DocumentStructure,
        preset_name: Optional[str] = None,
    ) -> bytes:
        """Compiles DocumentStructure into valid PDF binary bytes."""
        style = get_style_preset(preset_name) if preset_name else self._style_config

        logger.info(
            f"Generating PDF document [title: '{document.title or 'Untitled'}', preset: '{style.preset_name.value}']"
        )

        # 1. Resolve geometry & margins
        margin_left = style.margins.left_inches * 72.0
        margin_right = style.margins.right_inches * 72.0
        margin_top = style.margins.top_inches * 72.0
        margin_bottom = style.margins.bottom_inches * 72.0
        page_width, page_height = letter
        available_width = page_width - margin_left - margin_right

        # 2. Resolve ReportLab font names
        font_family, heading_font, code_font = self._resolve_fonts(style)

        # 3. Create ReportLab paragraph styles
        styles = self._build_stylesheet(style, font_family, heading_font, code_font)

        # 4. Construct flowables story
        story: List[Any] = []

        # 4a. Title (if not already present as first element)
        title_already_in_elements = any(
            e.type == DocumentElementType.TITLE for e in document.elements
        )
        if document.title and not title_already_in_elements:
            story.append(Paragraph(html.escape(document.title), styles["DocTitle"]))
            story.append(Spacer(1, 10))

        # 4b. Abstract (if provided)
        if document.abstract:
            story.append(Paragraph("<b>Abstract</b>", styles["AbstractHeading"]))
            story.append(Spacer(1, 4))
            formatted_abstract = self._format_inline_text(document.abstract)
            story.append(Paragraph(formatted_abstract, styles["AbstractBody"]))
            story.append(Spacer(1, 12))

        # 4c. Render Document Elements
        for elem in document.elements:
            self._render_element(story, elem, styles, available_width, style)

        # 4d. References (if not rendered inline from elements)
        references_rendered = any(
            e.type == DocumentElementType.REFERENCE_ITEM for e in document.elements
        )
        if document.references and not references_rendered:
            story.append(Spacer(1, 14))
            story.append(Paragraph("References", styles["Heading1"]))
            story.append(Spacer(1, 6))
            for ref in document.references:
                formatted_ref = self._format_inline_text(ref)
                story.append(Paragraph(formatted_ref, styles["ReferenceItem"]))
                story.append(Spacer(1, 4))

        # 5. Build PDF with NumberedCanvas in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=margin_left,
            rightMargin=margin_right,
            topMargin=margin_top,
            bottomMargin=margin_bottom,
        )

        def make_canvas(*args: Any, **kwargs: Any) -> NumberedCanvas:
            c = NumberedCanvas(*args, **kwargs)
            c.doc_title = document.title or "Academic Document"
            c.header_right = style.header_footer.header_right
            c.header_left = style.header_footer.header_left
            c.footer_center = style.header_footer.footer_center
            c.show_header = style.header_footer.show_header
            c.show_footer = style.header_footer.show_footer
            c.first_page_different = style.header_footer.first_page_different
            c.margin_left = margin_left
            c.margin_right = margin_right
            c.margin_top = margin_top
            c.margin_bottom = margin_bottom
            c.page_width = page_width
            c.page_height = page_height
            c.primary_font = font_family
            return c

        doc.build(story, canvasmaker=make_canvas)

        pdf_bytes = buffer.getvalue()
        buffer.close()

        logger.info(f"PDF compilation successful: {len(pdf_bytes)} bytes generated.")
        return pdf_bytes

    # -----------------------------------------------------------------------
    # Font Resolution & Style Mapping
    # -----------------------------------------------------------------------

    def _resolve_fonts(self, style: DocumentStyleConfig) -> Tuple[str, str, str]:
        """Maps typography configuration to standard PostScript font families."""
        p_name = style.fonts.primary.lower()
        if "arial" in p_name or "calibri" in p_name or "sans" in p_name:
            font_family = "Helvetica"
        elif "georgia" in p_name:
            font_family = "Times-Roman"
        else:
            font_family = "Times-Roman"

        h_name = style.fonts.heading.lower()
        if "arial" in h_name or "calibri" in h_name or "sans" in h_name:
            heading_font = "Helvetica"
        else:
            heading_font = "Times-Roman"

        code_font = "Courier"
        return font_family, heading_font, code_font

    def _build_stylesheet(
        self,
        style: DocumentStyleConfig,
        font_family: str,
        heading_font: str,
        code_font: str,
    ) -> StyleSheet1:
        """Constructs ReportLab StyleSheet adhering strictly to the centralized preset."""
        ss = StyleSheet1()

        if font_family == "Helvetica":
            body_font = "Helvetica"
            body_bold = "Helvetica-Bold"
            body_italic = "Helvetica-Oblique"
            body_bold_italic = "Helvetica-BoldOblique"
        else:
            body_font = "Times-Roman"
            body_bold = "Times-Bold"
            body_italic = "Times-Italic"
            body_bold_italic = "Times-BoldItalic"

        if heading_font == "Helvetica":
            head_bold = "Helvetica-Bold"
            head_italic = "Helvetica-Oblique"
            head_bold_italic = "Helvetica-BoldOblique"
        else:
            head_bold = "Times-Bold"
            head_italic = "Times-Italic"
            head_bold_italic = "Times-BoldItalic"

        # Colors
        text_color = colors.HexColor(f"#{style.colors.primary_text}")
        heading_color = colors.HexColor(f"#{style.colors.heading_text}")
        accent_color = colors.HexColor(f"#{style.colors.accent}")
        muted_color = colors.HexColor(f"#{style.colors.muted}")

        # Line spacing & leading calculation
        base_body_size = style.sizes.body
        if style.spacing.body_line_spacing >= 1.9:
            body_leading = base_body_size * 1.8
        elif style.spacing.body_line_spacing >= 1.4:
            body_leading = base_body_size * 1.45
        else:
            body_leading = base_body_size * 1.25

        # Title
        ss.add(
            ParagraphStyle(
                "DocTitle",
                fontName=head_bold,
                fontSize=style.sizes.title,
                leading=style.sizes.title * 1.2,
                textColor=heading_color,
                alignment=1,  # Center
                spaceAfter=12,
                keepWithNext=True,
            )
        )

        # Headings
        ss.add(
            ParagraphStyle(
                "Heading1",
                fontName=head_bold,
                fontSize=style.sizes.heading_1,
                leading=style.sizes.heading_1 * 1.25,
                textColor=heading_color,
                spaceBefore=style.spacing.heading_1_before_pt,
                spaceAfter=style.spacing.heading_1_after_pt,
                keepWithNext=True,
            )
        )
        ss.add(
            ParagraphStyle(
                "Heading2",
                fontName=head_bold,
                fontSize=style.sizes.heading_2,
                leading=style.sizes.heading_2 * 1.25,
                textColor=heading_color,
                spaceBefore=style.spacing.heading_2_before_pt,
                spaceAfter=style.spacing.heading_2_after_pt,
                keepWithNext=True,
            )
        )
        ss.add(
            ParagraphStyle(
                "Heading3",
                fontName=head_bold_italic,
                fontSize=style.sizes.heading_3,
                leading=style.sizes.heading_3 * 1.25,
                textColor=heading_color,
                spaceBefore=style.spacing.heading_3_before_pt,
                spaceAfter=style.spacing.heading_3_after_pt,
                keepWithNext=True,
            )
        )

        # Body Paragraph
        ss.add(
            ParagraphStyle(
                "BodyText",
                fontName=body_font,
                fontSize=base_body_size,
                leading=body_leading,
                textColor=text_color,
                firstLineIndent=style.spacing.body_first_line_indent_inches * 72.0,
                spaceAfter=style.spacing.body_space_after_pt,
            )
        )

        # Body Paragraph without first line indent (for after headings or quotes)
        ss.add(
            ParagraphStyle(
                "BodyTextNoIndent",
                fontName=body_font,
                fontSize=base_body_size,
                leading=body_leading,
                textColor=text_color,
                firstLineIndent=0,
                spaceAfter=style.spacing.body_space_after_pt + 3,
            )
        )

        # Abstract
        ss.add(
            ParagraphStyle(
                "AbstractHeading",
                fontName=head_bold,
                fontSize=style.sizes.abstract,
                leading=style.sizes.abstract * 1.2,
                textColor=heading_color,
                alignment=1,  # Center
                keepWithNext=True,
            )
        )
        ss.add(
            ParagraphStyle(
                "AbstractBody",
                fontName=body_italic,
                fontSize=style.sizes.abstract,
                leading=style.sizes.abstract * 1.35,
                textColor=text_color,
                leftIndent=36,
                rightIndent=36,
                firstLineIndent=0,
                alignment=4,  # Justify
            )
        )

        # Lists
        ss.add(
            ParagraphStyle(
                "ListItem",
                fontName=body_font,
                fontSize=base_body_size,
                leading=body_leading,
                textColor=text_color,
                leftIndent=24,
                firstLineIndent=-12,
                spaceAfter=style.spacing.list_item_space_after_pt,
            )
        )

        # Blockquote
        ss.add(
            ParagraphStyle(
                "Blockquote",
                fontName=body_italic,
                fontSize=base_body_size - 0.5,
                leading=(base_body_size - 0.5) * 1.35,
                textColor=colors.HexColor(f"#{style.colors.muted}"),
                leftIndent=36,
                rightIndent=36,
                spaceBefore=6,
                spaceAfter=6,
            )
        )

        # Math Display Block
        ss.add(
            ParagraphStyle(
                "MathDisplay",
                fontName=body_italic,
                fontSize=base_body_size + 0.5,
                leading=(base_body_size + 0.5) * 1.4,
                textColor=text_color,
                alignment=1,  # Centered
                spaceBefore=8,
                spaceAfter=8,
            )
        )

        # Table Cell
        ss.add(
            ParagraphStyle(
                "TableCell",
                fontName=body_font,
                fontSize=style.sizes.table_cell,
                leading=style.sizes.table_cell * 1.25,
                textColor=text_color,
            )
        )
        ss.add(
            ParagraphStyle(
                "TableHeaderCell",
                fontName=body_bold,
                fontSize=style.sizes.table_cell,
                leading=style.sizes.table_cell * 1.25,
                textColor=colors.HexColor(f"#{style.colors.table_header_text}"),
            )
        )
        ss.add(
            ParagraphStyle(
                "TableCaption",
                fontName=body_italic,
                fontSize=style.sizes.caption,
                leading=style.sizes.caption * 1.2,
                textColor=muted_color,
                spaceBefore=4,
                spaceAfter=4,
                keepWithNext=True,
            )
        )

        # Reference Item
        ss.add(
            ParagraphStyle(
                "ReferenceItem",
                fontName=body_font,
                fontSize=base_body_size - 0.5,
                leading=(base_body_size - 0.5) * 1.35,
                textColor=text_color,
                leftIndent=36,
                firstLineIndent=-36,  # Standard APA hanging indent (0.5 in)
                spaceAfter=6,
            )
        )

        return ss

    # -----------------------------------------------------------------------
    # Element Rendering Engine
    # -----------------------------------------------------------------------

    def _render_element(
        self,
        story: List[Any],
        elem: DocumentElement,
        styles: StyleSheet1,
        available_width: float,
        style: DocumentStyleConfig,
    ) -> None:
        """Dispatches DocumentElement to appropriate ReportLab flowable."""
        t = elem.type

        if t == DocumentElementType.TITLE:
            story.append(Paragraph(html.escape(elem.content), styles["DocTitle"]))
            story.append(Spacer(1, 10))

        elif t == DocumentElementType.HEADING:
            level = elem.level or 1
            style_key = f"Heading{min(level, 3)}"
            formatted_text = self._format_inline_text(elem.content)
            story.append(Paragraph(formatted_text, styles[style_key]))

        elif t == DocumentElementType.PARAGRAPH:
            # Use indented or non-indented body style based on indent config
            style_key = "BodyText" if style.spacing.body_first_line_indent_inches > 0 else "BodyTextNoIndent"
            formatted_text = self._format_inline_text(elem.content)
            story.append(Paragraph(formatted_text, styles[style_key]))

        elif t == DocumentElementType.ABSTRACT:
            story.append(Paragraph("<b>Abstract</b>", styles["AbstractHeading"]))
            story.append(Spacer(1, 4))
            formatted_text = self._format_inline_text(elem.content)
            story.append(Paragraph(formatted_text, styles["AbstractBody"]))
            story.append(Spacer(1, 12))

        elif t in (DocumentElementType.ORDERED_LIST, DocumentElementType.UNORDERED_LIST):
            self._render_list(story, elem, styles)

        elif t == DocumentElementType.TABLE:
            self._render_table(story, elem, styles, available_width, style)

        elif t == DocumentElementType.MATH_BLOCK:
            self._render_display_math(story, elem.content, styles)

        elif t == DocumentElementType.BLOCKQUOTE:
            formatted_text = self._format_inline_text(elem.content)
            story.append(Paragraph(formatted_text, styles["Blockquote"]))

        elif t == DocumentElementType.CODE_BLOCK:
            self._render_code_block(story, elem, styles, available_width, style)

        elif t == DocumentElementType.CITATION:
            formatted_text = self._format_inline_text(elem.content)
            story.append(Paragraph(formatted_text, styles["BodyTextNoIndent"]))

        elif t == DocumentElementType.REFERENCE_ITEM:
            formatted_text = self._format_inline_text(elem.content)
            story.append(Paragraph(formatted_text, styles["ReferenceItem"]))

        elif t == DocumentElementType.REFERENCE_LIST:
            story.append(Paragraph("References", styles["Heading1"]))
            story.append(Spacer(1, 6))
            if elem.items:
                for item in elem.items:
                    formatted_item = self._format_inline_text(item)
                    story.append(Paragraph(formatted_item, styles["ReferenceItem"]))
            elif elem.content:
                for line in elem.content.split("\n"):
                    line = line.strip()
                    if line:
                        formatted_line = self._format_inline_text(line)
                        story.append(Paragraph(formatted_line, styles["ReferenceItem"]))

    def _render_list(
        self,
        story: List[Any],
        elem: DocumentElement,
        styles: StyleSheet1,
    ) -> None:
        """Renders ordered and unordered lists with proper bullet/number formatting."""
        items = elem.items or ([elem.content] if elem.content else [])
        is_ordered = elem.type == DocumentElementType.ORDERED_LIST

        for idx, item in enumerate(items, start=1):
            prefix = f"{idx}. " if is_ordered else "&bull; "
            formatted_item = self._format_inline_text(item)
            story.append(Paragraph(f"{prefix}{formatted_item}", styles["ListItem"]))

    def _render_table(
        self,
        story: List[Any],
        elem: DocumentElement,
        styles: StyleSheet1,
        available_width: float,
        style: DocumentStyleConfig,
    ) -> None:
        """Renders academic tabular structure with column wrapping and styled borders."""
        table_data = elem.table_data or TableData()
        headers = table_data.headers or []
        rows = table_data.rows or []

        if not headers and not rows:
            return

        if table_data.caption:
            story.append(Paragraph(html.escape(table_data.caption), styles["TableCaption"]))

        # Calculate number of columns
        num_cols = max(len(headers), max((len(r) for r in rows), default=0))
        if num_cols == 0:
            return

        col_width = available_width / float(num_cols)
        col_widths = [col_width] * num_cols

        # Wrap text in Paragraphs to enable line wrapping within cells
        table_flowable_data: List[List[Any]] = []

        if headers:
            header_row = []
            for h in headers:
                cell_p = Paragraph(self._format_inline_text(h), styles["TableHeaderCell"])
                header_row.append(cell_p)
            table_flowable_data.append(header_row)

        for row in rows:
            data_row = []
            for c_idx in range(num_cols):
                val = row[c_idx] if c_idx < len(row) else ""
                cell_p = Paragraph(self._format_inline_text(val), styles["TableCell"])
                data_row.append(cell_p)
            table_flowable_data.append(data_row)

        table = Table(table_flowable_data, colWidths=col_widths, repeatRows=1 if headers else 0)

        t_style = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(f"#{style.colors.table_border}")),
        ]

        if headers:
            t_style.append(
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{style.colors.table_header_bg}"))
            )

        table.setStyle(TableStyle(t_style))
        story.append(Spacer(1, 4))
        story.append(table)
        story.append(Spacer(1, 8))

    def _render_display_math(
        self,
        story: List[Any],
        latex: str,
        styles: StyleSheet1,
    ) -> None:
        """Renders display math block as centered rich equation flowable."""
        rich_math = self._math_service.latex_to_rich_text(latex, is_display=True)
        story.append(Paragraph(rich_math, styles["MathDisplay"]))

    def _render_code_block(
        self,
        story: List[Any],
        elem: DocumentElement,
        styles: StyleSheet1,
        available_width: float,
        style: DocumentStyleConfig,
    ) -> None:
        """Renders monospaced syntax code block with background shading."""
        code_text = elem.content
        if not code_text:
            return

        code_style = ParagraphStyle(
            "CodeBlockText",
            fontName="Courier",
            fontSize=style.sizes.code_block,
            leading=style.sizes.code_block * 1.25,
            textColor=colors.HexColor(f"#{style.colors.code_text}"),
            leftIndent=8,
            rightIndent=8,
        )

        escaped_code = html.escape(code_text)
        p = Preformatted(escaped_code, code_style)

        # Enclose in single-cell Table for uniform background & border
        wrapper_table = Table([[p]], colWidths=[available_width])
        wrapper_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(f"#{style.colors.code_bg}")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(f"#{style.colors.code_border}")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        story.append(Spacer(1, 4))
        story.append(wrapper_table)
        story.append(Spacer(1, 6))

    # -----------------------------------------------------------------------
    # Inline Formatting & Math Pipeline
    # -----------------------------------------------------------------------

    def _format_inline_text(self, text: str) -> str:
        """Transforms text with bold, italic, code, and LaTeX math into ReportLab XML markup."""
        if not text:
            return ""

        # 1. Segment text for math constructs to protect formulas
        segments = self._math_service.segment_text(text)
        out_parts = []

        for seg in segments:
            if seg.is_math:
                # Convert LaTeX to rich mathematical Unicode with <sup>, <sub>
                rich_math = self._math_service.latex_to_rich_text(
                    seg.text, is_display=(seg.math_type == MathType.DISPLAY)
                )
                out_parts.append(rich_math)
            else:
                # Plain prose: safely escape and convert inline typography
                out_parts.append(self._format_prose(seg.text))

        return "".join(out_parts)

    def _format_prose(self, prose: str) -> str:
        """Escapes prose text and applies markdown typography tags (bold, italic, code)."""
        # 1. Escape HTML specials first
        s = html.escape(prose)

        # 2. Convert markdown bold (**text**)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)

        # 3. Convert markdown italic (*text*)
        s = re.sub(r"\*([^\*]+?)\*", r"<i>\1</i>", s)

        # 4. Convert inline code (`code`)
        s = re.sub(r"`([^`]+?)`", r'<font name="Courier">\1</font>', s)

        return s
