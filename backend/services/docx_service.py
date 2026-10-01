"""Professional DOCX Generation Engine for FormatAI.

Consumes the internal FormatAI DocumentStructure model and produces genuinely
editable Microsoft Word .docx files using python-docx and centralized style presets.

Features supported:
- Full document structure: Title, Heading 1, Heading 2, Heading 3, Paragraphs, Abstract
- Rich inline formatting: Bold, Italic, Underline, Inline Code, Inline Math, Citations
- Academic tabular data: Header rows, cell alignments, background shading, table borders
- Numbered and bulleted lists with precise hanging indents
- Academic quotations & blockquotes with indentation
- Math blocks and LaTeX representations with dedicated styling
- Monospaced code blocks with syntax background shading
- Page numbers in running footers/headers via Word XML fields
- Precise margins, paragraph line spacing, and font configuration
- Centralized presets: Academic (APA), Research Paper, Exam, Study Notes, Textbook
"""

import io
import re
from typing import List, Optional, Tuple

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

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


class DocxService:
    """Orchestrates Microsoft Word (.docx) document compilation from DocumentStructure."""

    def __init__(
        self,
        style_config: Optional[DocumentStyleConfig] = None,
        math_service: Optional[MathService] = None,
    ):
        self._style_config = style_config or get_style_preset(StylePresetName.ACADEMIC.value)
        self._math_service = math_service or MathService()

    def generate_docx(
        self,
        document: DocumentStructure,
        preset_name: Optional[str] = None,
    ) -> bytes:
        """Compiles DocumentStructure into valid editable .docx binary bytes."""
        style = get_style_preset(preset_name) if preset_name else self._style_config

        logger.info(
            f"Generating DOCX document [title: '{document.title or 'Untitled'}', preset: '{style.preset_name.value}']"
        )

        doc = Document()
        self._configure_document_styles(doc, style)
        self._configure_page_setup(doc, style, document.title)

        # 1. Title (if present and not already first element)
        title_already_in_elements = any(
            e.type == DocumentElementType.TITLE for e in document.elements
        )
        if document.title and not title_already_in_elements:
            self._add_title(doc, document.title, style)

        # 2. Abstract (if provided at document root)
        if document.abstract:
            self._add_abstract(doc, document.abstract, style)

        # 3. Document Elements
        for elem in document.elements:
            self._render_element(doc, elem, style)

        # 4. References (if not rendered inline from elements)
        references_rendered = any(
            e.type == DocumentElementType.REFERENCE_ITEM for e in document.elements
        )
        if document.references and not references_rendered:
            self._add_references_section(doc, document.references, style)

        # Save to memory buffer
        buffer = io.BytesIO()
        doc.save(buffer)
        docx_bytes = buffer.getvalue()
        buffer.close()

        logger.info(f"DOCX compilation successful: {len(docx_bytes)} bytes generated.")
        return docx_bytes

    # -----------------------------------------------------------------------
    # Document Setup & Styling
    # -----------------------------------------------------------------------

    def _hex_to_rgb(self, hex_str: str) -> RGBColor:
        """Converts 6-character hex string to docx RGBColor."""
        clean_hex = hex_str.lstrip("#")
        if len(clean_hex) != 6:
            return RGBColor(0, 0, 0)
        return RGBColor(
            int(clean_hex[0:2], 16),
            int(clean_hex[2:4], 16),
            int(clean_hex[4:6], 16),
        )

    def _configure_document_styles(self, doc: Document, style: DocumentStyleConfig) -> None:
        """Sets default font families, sizes, and colors on document Normal style."""
        normal_style = doc.styles["Normal"]
        font = normal_style.font
        font.name = style.fonts.primary
        font.size = Pt(style.sizes.body)
        font.color.rgb = self._hex_to_rgb(style.colors.primary_text)

    def _configure_page_setup(
        self,
        doc: Document,
        style: DocumentStyleConfig,
        doc_title: Optional[str],
    ) -> None:
        """Sets up 1-inch margins, running heads, and page numbers."""
        for section in doc.sections:
            section.top_margin = Inches(style.margins.top_inches)
            section.bottom_margin = Inches(style.margins.bottom_inches)
            section.left_margin = Inches(style.margins.left_inches)
            section.right_margin = Inches(style.margins.right_inches)
            section.header_distance = Inches(style.margins.header_inches)
            section.footer_distance = Inches(style.margins.footer_inches)

            # Header / Footer configuration
            hf_cfg = style.header_footer
            if hf_cfg.first_page_different:
                section.different_first_page_header_footer = True

            # Running Header
            if hf_cfg.show_header:
                header = section.header
                p_head = header.paragraphs[0]
                p_head.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p_head.paragraph_format.space_after = Pt(0)
                p_head.paragraph_format.line_spacing = 1.0

                head_text = hf_cfg.header_right or (doc_title[:40] if doc_title else "FormatAI")
                r_head = p_head.add_run(head_text)
                r_head.font.name = style.fonts.primary
                r_head.font.size = Pt(style.sizes.header_footer)
                r_head.font.color.rgb = self._hex_to_rgb(style.colors.muted)

            # Footer with page number field
            if hf_cfg.show_footer:
                footer = section.footer
                p_foot = footer.paragraphs[0]
                p_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_foot.paragraph_format.space_after = Pt(0)
                p_foot.paragraph_format.line_spacing = 1.0

                if hf_cfg.show_page_number_in_footer:
                    r_prefix = p_foot.add_run("Page ")
                    r_prefix.font.name = style.fonts.primary
                    r_prefix.font.size = Pt(style.sizes.header_footer)
                    r_prefix.font.color.rgb = self._hex_to_rgb(style.colors.muted)
                    self._add_page_number_field(p_foot)

    def _add_page_number_field(self, paragraph) -> None:
        """Injects dynamic Word PAGE field code for automated page numbering."""
        fldSimple = OxmlElement("w:fldSimple")
        fldSimple.set(qn("w:instr"), "PAGE")
        paragraph._p.append(fldSimple)

    # -----------------------------------------------------------------------
    # Content Block Renderers
    # -----------------------------------------------------------------------

    def _render_element(
        self,
        doc: Document,
        elem: DocumentElement,
        style: DocumentStyleConfig,
    ) -> None:
        """Dispatches an element to its specialized renderer."""
        elem_type = elem.type

        if elem_type == DocumentElementType.TITLE:
            self._add_title(doc, elem.content, style)
        elif elem_type == DocumentElementType.HEADING:
            self._add_heading(doc, elem.content, elem.level or 1, style)
        elif elem_type == DocumentElementType.PARAGRAPH:
            self._add_paragraph(doc, elem.content, style)
        elif elem_type == DocumentElementType.ABSTRACT:
            self._add_abstract(doc, elem.content, style)
        elif elem_type == DocumentElementType.UNORDERED_LIST:
            self._add_unordered_list(doc, elem.items or [elem.content], style)
        elif elem_type == DocumentElementType.ORDERED_LIST:
            self._add_ordered_list(doc, elem.items or [elem.content], style)
        elif elem_type == DocumentElementType.TABLE:
            if elem.table_data:
                self._add_table(doc, elem.table_data, style)
            else:
                self._add_paragraph(doc, elem.content, style)
        elif elem_type == DocumentElementType.BLOCKQUOTE:
            self._add_blockquote(doc, elem.content, style)
        elif elem_type == DocumentElementType.CODE_BLOCK:
            self._add_code_block(doc, elem.content, elem.language, style)
        elif elem_type == DocumentElementType.MATH_BLOCK:
            self._add_math_block(doc, elem.content, style)
        elif elem_type == DocumentElementType.REFERENCE_ITEM:
            self._add_reference_item(doc, elem.content, style)

    def _add_title(self, doc: Document, title_text: str, style: DocumentStyleConfig) -> None:
        """Renders prominent academic title."""
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(24)
        p.paragraph_format.space_after = Pt(12)
        p.paragraph_format.line_spacing = 1.2
        p.paragraph_format.keep_with_next = True

        run = p.add_run(title_text)
        run.bold = True
        run.font.name = style.fonts.heading
        run.font.size = Pt(style.sizes.title)
        run.font.color.rgb = self._hex_to_rgb(style.colors.heading_text)

    def _add_abstract(self, doc: Document, abstract_text: str, style: DocumentStyleConfig) -> None:
        """Renders formal Abstract section with centered heading and block text."""
        # Abstract heading
        h = doc.add_paragraph()
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.keep_with_next = True

        r_head = h.add_run("Abstract")
        r_head.bold = True
        r_head.font.name = style.fonts.heading
        r_head.font.size = Pt(style.sizes.heading_2)
        r_head.font.color.rgb = self._hex_to_rgb(style.colors.heading_text)

        # Abstract content
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if style.preset_name != StylePresetName.ACADEMIC else WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing = style.spacing.body_line_spacing
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(12)
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.right_indent = Inches(0.5)

        self._append_formatted_text(p, abstract_text, style, base_size=style.sizes.abstract)

    def _add_heading(
        self,
        doc: Document,
        text: str,
        level: int,
        style: DocumentStyleConfig,
    ) -> None:
        """Renders Heading 1, Heading 2, or Heading 3 with proper hierarchy & typography."""
        p = doc.add_paragraph()
        p.paragraph_format.keep_with_next = True

        # Heading Level 1
        if level <= 1:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if style.preset_name == StylePresetName.ACADEMIC else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(style.spacing.heading_1_before_pt)
            p.paragraph_format.space_after = Pt(style.spacing.heading_1_after_pt)
            size = style.sizes.heading_1
        # Heading Level 2
        elif level == 2:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(style.spacing.heading_2_before_pt)
            p.paragraph_format.space_after = Pt(style.spacing.heading_2_after_pt)
            size = style.sizes.heading_2
        # Heading Level 3+
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(style.spacing.heading_3_before_pt)
            p.paragraph_format.space_after = Pt(style.spacing.heading_3_after_pt)
            size = style.sizes.heading_3

        p.paragraph_format.line_spacing = 1.15

        run = p.add_run(text)
        run.bold = True
        run.font.name = style.fonts.heading
        run.font.size = Pt(size)
        run.font.color.rgb = self._hex_to_rgb(style.colors.heading_text)

    def _add_paragraph(self, doc: Document, text: str, style: DocumentStyleConfig) -> None:
        """Renders standard academic body paragraph with line spacing and indent."""
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing = style.spacing.body_line_spacing
        p.paragraph_format.space_after = Pt(style.spacing.body_space_after_pt)
        p.paragraph_format.space_before = Pt(0)

        # Apply first line indent if configured (e.g. APA standard 0.5 in)
        if style.spacing.body_first_line_indent_inches > 0:
            p.paragraph_format.first_line_indent = Inches(style.spacing.body_first_line_indent_inches)

        self._append_formatted_text(p, text, style, base_size=style.sizes.body)

    def _add_unordered_list(
        self,
        doc: Document,
        items: List[str],
        style: DocumentStyleConfig,
    ) -> None:
        """Renders bulleted list items with standard bullet indentation."""
        for item in items:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.left_indent = Inches(0.5)
            p.paragraph_format.first_line_indent = Inches(-0.25)
            p.paragraph_format.space_after = Pt(style.spacing.list_item_space_after_pt)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.line_spacing = 1.15

            # Bullet symbol
            r_bullet = p.add_run("•\t")
            r_bullet.font.name = style.fonts.primary
            r_bullet.font.size = Pt(style.sizes.body)

            self._append_formatted_text(p, item, style, base_size=style.sizes.body)

    def _add_ordered_list(
        self,
        doc: Document,
        items: List[str],
        style: DocumentStyleConfig,
    ) -> None:
        """Renders numbered list items with sequence formatting."""
        for idx, item in enumerate(items, start=1):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.left_indent = Inches(0.5)
            p.paragraph_format.first_line_indent = Inches(-0.25)
            p.paragraph_format.space_after = Pt(style.spacing.list_item_space_after_pt)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.line_spacing = 1.15

            # Number prefix
            r_num = p.add_run(f"{idx}.\t")
            r_num.font.name = style.fonts.primary
            r_num.font.size = Pt(style.sizes.body)
            r_num.bold = True

            self._append_formatted_text(p, item, style, base_size=style.sizes.body)

    def _add_table(
        self,
        doc: Document,
        table_data: TableData,
        style: DocumentStyleConfig,
    ) -> None:
        """Builds a structured, beautifully styled Microsoft Word table."""
        num_cols = len(table_data.headers)
        if num_cols == 0:
            return

        num_rows = len(table_data.rows) + 1
        table = doc.add_table(rows=num_rows, cols=num_cols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Configure table borders via Word XML
        self._apply_table_borders(table, style.colors.table_border)

        # 1. Header Row
        header_row = table.rows[0]
        # Repeat header row across multiple pages
        trPr = header_row._tr.get_or_add_trPr()
        trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
        trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))

        for col_idx, header_text in enumerate(table_data.headers):
            cell = header_row.cells[col_idx]
            # Apply cell background shading
            self._set_cell_shading(cell, style.colors.table_header_bg)
            self._set_cell_margins(cell, top=120, bottom=120, left=150, right=150)

            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.0

            # Alignment
            align = table_data.alignments[col_idx] if col_idx < len(table_data.alignments) else TableColumnAlign.LEFT
            p.alignment = self._map_table_align(align)

            run = p.add_run(header_text)
            run.bold = style.table_header_bold
            run.font.name = style.fonts.heading
            run.font.size = Pt(style.sizes.table_cell)
            run.font.color.rgb = self._hex_to_rgb(style.colors.table_header_text)

        # 2. Data Rows
        for row_idx, row_values in enumerate(table_data.rows, start=1):
            row = table.rows[row_idx]
            trPr = row._tr.get_or_add_trPr()
            trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))

            # Optional zebra striping
            is_even = (row_idx % 2 == 0)
            if style.table_has_zebra_shading and is_even:
                row_bg = "FAFAFA"
            else:
                row_bg = None

            for col_idx, cell_value in enumerate(row_values):
                if col_idx >= num_cols:
                    break
                cell = row.cells[col_idx]
                if row_bg:
                    self._set_cell_shading(cell, row_bg)
                self._set_cell_margins(cell, top=100, bottom=100, left=150, right=150)

                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.0

                align = table_data.alignments[col_idx] if col_idx < len(table_data.alignments) else TableColumnAlign.LEFT
                p.alignment = self._map_table_align(align)

                self._append_formatted_text(p, cell_value, style, base_size=style.sizes.table_cell)

        # Add spacing after table
        p_after = doc.add_paragraph()
        p_after.paragraph_format.space_before = Pt(0)
        p_after.paragraph_format.space_after = Pt(6)

    def _map_table_align(self, align: TableColumnAlign) -> WD_ALIGN_PARAGRAPH:
        if align == TableColumnAlign.CENTER:
            return WD_ALIGN_PARAGRAPH.CENTER
        elif align == TableColumnAlign.RIGHT:
            return WD_ALIGN_PARAGRAPH.RIGHT
        return WD_ALIGN_PARAGRAPH.LEFT

    def _set_cell_shading(self, cell, hex_color: str) -> None:
        """Sets XML background fill color on table cell."""
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color.lstrip("#")}"/>')
        cell._tc.get_or_add_tcPr().append(shading)

    def _set_cell_margins(self, cell, top=100, bottom=100, left=150, right=150) -> None:
        """Sets cell padding margins in twips (1/20 of a point)."""
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = parse_xml(
            f'<w:tcMar {nsdecls("w")}>\n'
            f'  <w:top w:w="{top}" w:type="dxa"/>\n'
            f'  <w:bottom w:w="{bottom}" w:type="dxa"/>\n'
            f'  <w:left w:w="{left}" w:type="dxa"/>\n'
            f'  <w:right w:w="{right}" w:type="dxa"/>\n'
            f'</w:tcMar>'
        )
        tcPr.append(tcMar)

    def _apply_table_borders(self, table, border_color: str) -> None:
        """Applies clean academic table borders (APA style top/bottom rules)."""
        clean_color = border_color.lstrip("#")
        tblPr = table._tbl.tblPr
        tblBorders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>\n'
            f'  <w:top w:val="single" w:sz="8" w:space="0" w:color="{clean_color}"/>\n'
            f'  <w:bottom w:val="single" w:sz="8" w:space="0" w:color="{clean_color}"/>\n'
            f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E0E0E0"/>\n'
            f'  <w:insideV w:val="none"/>\n'
            f'  <w:left w:val="none"/>\n'
            f'  <w:right w:val="none"/>\n'
            f'</w:tblBorders>'
        )
        tblPr.append(tblBorders)

    def _add_blockquote(self, doc: Document, text: str, style: DocumentStyleConfig) -> None:
        """Renders academic blockquote indented with italicized text."""
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if style.preset_name != StylePresetName.ACADEMIC else WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.right_indent = Inches(0.5)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.15

        self._append_formatted_text(p, text, style, base_size=style.sizes.body, force_italic=True)

    def _add_code_block(
        self,
        doc: Document,
        code_text: str,
        language: Optional[str],
        style: DocumentStyleConfig,
    ) -> None:
        """Renders monospaced code block with subtle background shading."""
        # Use single-cell table for framed code block with background shading
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        self._set_cell_shading(cell, style.colors.code_bg)
        self._set_cell_margins(cell, top=120, bottom=120, left=180, right=180)

        # Border for code frame
        tcPr = cell._tc.get_or_add_tcPr()
        tcBorders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>\n'
            f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="{style.colors.code_border}"/>\n'
            f'  <w:left w:val="single" w:sz="4" w:space="0" w:color="{style.colors.code_border}"/>\n'
            f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{style.colors.code_border}"/>\n'
            f'  <w:right w:val="single" w:sz="4" w:space="0" w:color="{style.colors.code_border}"/>\n'
            f'</w:tcBorders>'
        )
        tcPr.append(tcBorders)

        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0

        for line_idx, line in enumerate(code_text.split("\n")):
            if line_idx > 0:
                p = cell.add_paragraph()
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0

            run = p.add_run(line if line else " ")
            run.font.name = style.fonts.code
            run.font.size = Pt(style.sizes.code_block)
            run.font.color.rgb = self._hex_to_rgb(style.colors.code_text)

        # Spacer paragraph after table
        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_before = Pt(0)
        p_sp.paragraph_format.space_after = Pt(6)

    def _add_math_block(self, doc: Document, math_content: str, style: DocumentStyleConfig) -> None:
        """Renders centered display mathematical expression using native Word OMML."""
        self._math_service.render_display_math_block(doc, math_content, style)

    def _add_reference_item(self, doc: Document, text: str, style: DocumentStyleConfig) -> None:
        """Renders reference bibliography entry with standard hanging indent."""
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.5)
        p.paragraph_format.line_spacing = 1.5 if style.preset_name != StylePresetName.ACADEMIC else 2.0
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.space_before = Pt(0)

        self._append_formatted_text(p, text, style, base_size=style.sizes.body)

    def _add_references_section(
        self,
        doc: Document,
        references: List[str],
        style: DocumentStyleConfig,
    ) -> None:
        """Appends References section heading and entries."""
        self._add_heading(doc, "References", level=2, style=style)
        for ref in references:
            self._add_reference_item(doc, ref, style)

    # -----------------------------------------------------------------------
    # Inline Formatting Parser & Run Appender
    # -----------------------------------------------------------------------

    def _append_formatted_text(
        self,
        paragraph,
        raw_text: str,
        style: DocumentStyleConfig,
        base_size: float,
        force_italic: bool = False,
    ) -> None:
        """Parses academic prose, detecting math expressions and markdown tokens.

        Compiles mathematical expressions into native Word OMML equations and
        prose into styled text runs.
        """
        if not raw_text:
            return

        # 1. Segment text into plain prose vs mathematics
        segments = self._math_service.segment_text(raw_text)

        for segment in segments:
            if segment.is_math and segment.latex:
                # Render native Word OMML mathematical equation
                self._math_service.render_math_to_paragraph(
                    paragraph=paragraph,
                    latex=segment.latex,
                    is_display=(segment.math_type == MathType.DISPLAY),
                    fallback_font=style.fonts.math,
                    fallback_size_pt=base_size,
                )
            else:
                # Render prose with standard markdown runs (bold, italic, code, etc.)
                self._append_inline_prose(
                    paragraph=paragraph,
                    prose_text=segment.text,
                    style=style,
                    base_size=base_size,
                    force_italic=force_italic,
                )

    def _sanitize_xml(self, text: str) -> str:
        """Removes XML-incompatible control characters (e.g. \x00-\x08, \x0b-\x0c, \x0e-\x1f)."""
        if not text:
            return ""
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(text))

    def _append_inline_prose(
        self,
        paragraph,
        prose_text: str,
        style: DocumentStyleConfig,
        base_size: float,
        force_italic: bool = False,
    ) -> None:
        """Appends formatted runs (**bold**, *italic*, <u>underline</u>, `code`, [citations])

        to the target paragraph for non-mathematical text chunks.
        """
        if not prose_text:
            return

        token_pattern = re.compile(
            r"(\*\*[^*]+?\*\*|\*[^*]+?\*|<u>[^<]+?</u>|`[^`]+?`|\[\d+(?:\s*[,-]\s*\d+)*\])"
        )

        pos = 0
        for match in token_pattern.finditer(prose_text):
            if match.start() > pos:
                plain_chunk = self._sanitize_xml(prose_text[pos:match.start()])
                run = paragraph.add_run(plain_chunk)
                run.font.name = style.fonts.primary
                run.font.size = Pt(base_size)
                run.font.color.rgb = self._hex_to_rgb(style.colors.primary_text)
                if force_italic:
                    run.italic = True

            token = match.group(1)

            if token.startswith("**") and token.endswith("**"):
                run = paragraph.add_run(self._sanitize_xml(token[2:-2]))
                run.bold = True
                run.font.name = style.fonts.primary
                run.font.size = Pt(base_size)
                run.font.color.rgb = self._hex_to_rgb(style.colors.primary_text)
                if force_italic:
                    run.italic = True

            elif token.startswith("*") and token.endswith("*"):
                run = paragraph.add_run(self._sanitize_xml(token[1:-1]))
                run.italic = True
                run.font.name = style.fonts.primary
                run.font.size = Pt(base_size)
                run.font.color.rgb = self._hex_to_rgb(style.colors.primary_text)

            elif token.startswith("<u>") and token.endswith("</u>"):
                run = paragraph.add_run(self._sanitize_xml(token[3:-4]))
                run.underline = True
                run.font.name = style.fonts.primary
                run.font.size = Pt(base_size)
                run.font.color.rgb = self._hex_to_rgb(style.colors.primary_text)
                if force_italic:
                    run.italic = True

            elif token.startswith("`") and token.endswith("`"):
                run = paragraph.add_run(self._sanitize_xml(token[1:-1]))
                run.font.name = style.fonts.code
                run.font.size = Pt(base_size * 0.9)
                run.font.color.rgb = self._hex_to_rgb(style.colors.code_text)

            elif token.startswith("[") and token.endswith("]"):
                run = paragraph.add_run(self._sanitize_xml(token))
                run.font.name = style.fonts.primary
                run.font.size = Pt(base_size)
                run.font.color.rgb = self._hex_to_rgb(style.colors.accent)
                if force_italic:
                    run.italic = True

            pos = match.end()

        if pos < len(prose_text):
            tail_chunk = self._sanitize_xml(prose_text[pos:])
            run = paragraph.add_run(tail_chunk)
            run.font.name = style.fonts.primary
            run.font.size = Pt(base_size)
            run.font.color.rgb = self._hex_to_rgb(style.colors.primary_text)
            if force_italic:
                run.italic = True
