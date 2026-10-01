"""Core Document Service orchestrating the complete academic processing pipeline.

Pipeline stages:
Raw Input
→ Content Analysis
→ Content Cleanup
→ Structure Detection
→ Formatting Rules
→ Document Model
"""

import math
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from backend.core.config import Settings
from backend.core.logging import logger
from backend.models.document import (
    DocumentAnalysis,
    DocumentElement,
    DocumentElementType,
    DocumentProcessingOptions,
    DocumentProcessRequest,
    DocumentProcessResponse,
    DocumentStats,
    DocumentStructure,
    EntityType,
)
from backend.services.content_cleanup_service import ContentCleanupService
from backend.services.formatting_service import FormattingService
from backend.skills.orchestrator import SkillOrchestrator
from backend.utils.markdown import (
    extract_heading_info,
    is_blockquote,
    is_list_item,
    is_table_row,
    parse_markdown_table,
)
from backend.utils.text_processing import (
    extract_inline_entities,
)


class DocumentService:
    """Orchestrator for academic document structure analysis, cleanup, and modeling."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        content_cleanup_service: Optional[ContentCleanupService] = None,
        formatting_service: Optional[FormattingService] = None,
        skill_orchestrator: Optional[SkillOrchestrator] = None,
    ):
        self._settings = settings
        self._content_cleanup = content_cleanup_service or ContentCleanupService()
        self._formatting = formatting_service or FormattingService()
        self._skill_orchestrator = skill_orchestrator or SkillOrchestrator()

    def process(self, request: DocumentProcessRequest) -> DocumentProcessResponse:
        """Executes the complete document processing pipeline:
        Input → Skill Orchestrator → Enabled Skills → Document Model → Export
        """
        raw_text = request.raw_text
        options = request.options

        logger.info(f"Processing academic document through Skill Orchestrator: {len(raw_text)} chars")

        # 1. Content Analysis (pre-transformation assessment)
        analysis = self.analyze_content(raw_text)

        # 2. Skill Orchestrator (Enabled Skills processing)
        orchestration = self._skill_orchestrator.run_pipeline(
            text=raw_text,
            enabled_skills=options.enabled_skills,
            disabled_skills=options.disabled_skills,
            context={
                "target_style": options.target_style,
                "smart_typography": options.smart_typography,
                "enable_content_cleanup": options.enable_content_cleanup,
                "enable_formatting_cleanup": options.enable_formatting_cleanup,
            },
        )

        diagnostics = list(analysis.diagnostics)
        if orchestration.all_diagnostics:
            diagnostics.extend(orchestration.all_diagnostics)
        analysis.diagnostics = diagnostics

        # 3. Structure Detection on the skill-transformed text
        elements = self.detect_structure(orchestration.final_text)

        # 4. Build Internal Document Model
        document = self.build_document_model(elements)

        # Update analysis title if detected during structure phase
        if not analysis.detected_title and document.title:
            analysis.detected_title = document.title

        return DocumentProcessResponse(
            success=True,
            document=document,
            analysis=analysis,
            executed_skills=orchestration.executed_skills,
            skipped_skills=orchestration.skipped_skills,
            pipeline_stages={
                "raw_char_count": len(raw_text),
                "processed_char_count": len(orchestration.final_text),
                "total_elements_detected": len(elements),
                "skills_pipeline_duration_ms": orchestration.total_execution_time_ms,
            },
        )

    def analyze_content(self, text: str) -> DocumentAnalysis:
        """Examines raw academic text to evaluate quality, title, abstract, references, and math density."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # Detect title candidate (first H1 or top prominent line)
        detected_title = None
        for line in lines[:5]:
            h_info = extract_heading_info(line)
            if h_info and h_info[0] == 1:
                detected_title = h_info[1]
                break
        if not detected_title and lines:
            if not lines[0].startswith(("#", "-", "*", "|", ">", "```", "$")):
                detected_title = lines[0]

        # Check for Abstract section
        has_abstract = bool(re.search(r"(?:^|\n)#{1,3}\s*Abstract\b|^\s*Abstract:\s*", text, re.IGNORECASE))

        # Check for References section
        has_references = bool(
            re.search(r"(?:^|\n)#{1,3}\s*(?:References|Bibliography|Works Cited)\b", text, re.IGNORECASE)
        )

        # Inline entities preview
        entities = extract_inline_entities(text)
        entities_summary: Dict[str, int] = {}
        for e in entities:
            key = e.entity_type.value
            entities_summary[key] = entities_summary.get(key, 0) + 1

        citation_count = entities_summary.get(EntityType.CITATION_REFERENCE.value, 0)
        math_count = (
            entities_summary.get(EntityType.INLINE_MATH.value, 0)
            + entities_summary.get(EntityType.DISPLAY_MATH.value, 0)
        )

        total_words = max(len(text.split()), 1)
        math_density = round((math_count / total_words) * 100, 2)

        # Heading hierarchy validation
        heading_levels: List[int] = []
        for line in lines:
            m = re.match(r"^(#{1,6})\s+", line)
            if m:
                heading_levels.append(len(m.group(1)))

        hierarchy_issues: List[str] = []
        for i in range(1, len(heading_levels)):
            if heading_levels[i] > heading_levels[i - 1] + 1:
                hierarchy_issues.append(
                    f"Heading leap detected: jumped from level {heading_levels[i - 1]} to {heading_levels[i]}"
                )

        # Compute initial structural quality score
        score = 100.0
        if hierarchy_issues:
            score -= 15.0
        if not has_references:
            score -= 10.0
        if not detected_title:
            score -= 15.0
        score = max(score, 20.0)

        diagnostics: List[str] = []
        if has_abstract:
            diagnostics.append("Detected formal Abstract section.")
        if has_references:
            diagnostics.append("Detected formal References/Bibliography section.")
        if citation_count > 0:
            diagnostics.append(f"Identified {citation_count} academic citation references.")
        if math_count > 0:
            diagnostics.append(f"Identified {math_count} mathematical expressions / LaTeX formulas.")

        return DocumentAnalysis(
            detected_title=detected_title,
            has_abstract=has_abstract,
            has_references=has_references,
            detected_style_candidate="APA" if not re.search(r"\[\d+\]", text) else "IEEE",
            heading_hierarchy_valid=len(hierarchy_issues) == 0,
            hierarchy_issues=hierarchy_issues,
            math_density=math_density,
            structure_quality_score=round(score, 1),
            detected_entities_summary=entities_summary,
            diagnostics=diagnostics,
        )

    def detect_structure(self, text: str) -> List[DocumentElement]:
        """Parses formatted document into structured DocumentElement sequence."""
        elements: List[DocumentElement] = []
        lines = text.split("\n")
        n = len(lines)
        i = 0
        in_references_section = False

        while i < n:
            line = lines[i]
            trimmed = line.strip()

            if not trimmed:
                i += 1
                continue

            # 1. Fenced Code Block
            if trimmed.startswith("```"):
                lang = trimmed[3:].strip()
                code_lines: List[str] = []
                raw_block = [line]
                i += 1
                while i < n and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    raw_block.append(lines[i])
                    i += 1
                if i < n:
                    raw_block.append(lines[i])
                    i += 1
                code_content = "\n".join(code_lines)
                elements.append(
                    DocumentElement(
                        id=str(uuid.uuid4())[:8],
                        type=DocumentElementType.CODE_BLOCK,
                        content=code_content,
                        raw_content="\n".join(raw_block),
                        language=lang or None,
                    )
                )
                continue

            # 2. Display Math Block ($$...$$ or LaTeX environment)
            if trimmed.startswith("$$"):
                math_lines: List[str] = []
                raw_block = [line]
                if trimmed.endswith("$$") and len(trimmed) > 4:
                    math_content = trimmed[2:-2].strip()
                    i += 1
                else:
                    i += 1
                    while i < n and not lines[i].strip().startswith("$$"):
                        math_lines.append(lines[i])
                        raw_block.append(lines[i])
                        i += 1
                    if i < n:
                        raw_block.append(lines[i])
                        i += 1
                    math_content = "\n".join(math_lines).strip()

                elements.append(
                    DocumentElement(
                        id=str(uuid.uuid4())[:8],
                        type=DocumentElementType.MATH_BLOCK,
                        content=math_content,
                        raw_content="\n".join(raw_block),
                        math_syntax="latex",
                    )
                )
                continue

            # 3. Headings
            h_info = extract_heading_info(line)
            if h_info:
                lvl, title = h_info
                # Track if entering References or Bibliography section
                if re.match(r"^(?:References|Bibliography|Works Cited)$", title, re.IGNORECASE):
                    in_references_section = True
                else:
                    in_references_section = False

                # Level 1 heading before any other headings is treated as TITLE
                is_first_h1 = (lvl == 1) and not any(
                    e.type in (DocumentElementType.TITLE, DocumentElementType.HEADING) for e in elements
                )
                elem_type = DocumentElementType.TITLE if is_first_h1 else DocumentElementType.HEADING

                elements.append(
                    DocumentElement(
                        id=str(uuid.uuid4())[:8],
                        type=elem_type,
                        content=title,
                        raw_content=line,
                        level=lvl,
                        entities=extract_inline_entities(title),
                    )
                )
                i += 1
                continue

            # 4. Markdown Tables
            if is_table_row(line):
                table_lines = [line]
                i += 1
                while i < n and (is_table_row(lines[i]) or lines[i].strip().startswith("|")):
                    table_lines.append(lines[i])
                    i += 1
                table_data = parse_markdown_table(table_lines)
                if table_data:
                    elements.append(
                        DocumentElement(
                            id=str(uuid.uuid4())[:8],
                            type=DocumentElementType.TABLE,
                            content=f"Table ({len(table_data.headers)} columns, {len(table_data.rows)} rows)",
                            raw_content="\n".join(table_lines),
                            table_data=table_data,
                        )
                    )
                    continue
                else:
                    # Fallback to paragraph if table parsing fails
                    content = "\n".join(table_lines)
                    elements.append(
                        DocumentElement(
                            id=str(uuid.uuid4())[:8],
                            type=DocumentElementType.PARAGRAPH,
                            content=content,
                            raw_content=content,
                            entities=extract_inline_entities(content),
                        )
                    )
                    continue

            # 5. Blockquotes
            is_quote, quote_content = is_blockquote(line)
            if is_quote:
                quote_lines = [quote_content or ""]
                raw_quote = [line]
                i += 1
                while i < n and lines[i].strip().startswith(">"):
                    _, next_q = is_blockquote(lines[i])
                    quote_lines.append(next_q or "")
                    raw_quote.append(lines[i])
                    i += 1
                full_quote = " ".join(quote_lines).strip()
                elements.append(
                    DocumentElement(
                        id=str(uuid.uuid4())[:8],
                        type=DocumentElementType.BLOCKQUOTE,
                        content=full_quote,
                        raw_content="\n".join(raw_quote),
                        entities=extract_inline_entities(full_quote),
                    )
                )
                continue

            # 6. Lists (Ordered and Unordered)
            is_list, list_type, item_text = is_list_item(line)
            if is_list:
                items: List[str] = [item_text or ""]
                raw_list: List[str] = [line]
                i += 1
                while i < n:
                    next_is_list, next_type, next_item = is_list_item(lines[i])
                    if next_is_list and next_type == list_type:
                        items.append(next_item or "")
                        raw_list.append(lines[i])
                        i += 1
                    elif lines[i].strip().startswith((" ", "\t")) and items:
                        # Indented list continuation
                        items[-1] += " " + lines[i].strip()
                        raw_list.append(lines[i])
                        i += 1
                    else:
                        break

                if in_references_section:
                    # Treat each item as reference entry
                    for ref_item in items:
                        elements.append(
                            DocumentElement(
                                id=str(uuid.uuid4())[:8],
                                type=DocumentElementType.REFERENCE_ITEM,
                                content=ref_item,
                                raw_content=ref_item,
                                entities=extract_inline_entities(ref_item),
                            )
                        )
                else:
                    elem_type = (
                        DocumentElementType.ORDERED_LIST
                        if list_type == "ordered"
                        else DocumentElementType.UNORDERED_LIST
                    )
                    elements.append(
                        DocumentElement(
                            id=str(uuid.uuid4())[:8],
                            type=elem_type,
                            content="\n".join(items),
                            raw_content="\n".join(raw_list),
                            items=items,
                            entities=extract_inline_entities(" ".join(items)),
                        )
                    )
                continue

            # 7. Standard Paragraph / Reference Item
            para_lines = [trimmed]
            raw_para = [line]
            i += 1
            while i < n:
                next_trimmed = lines[i].strip()
                if not next_trimmed:
                    break
                # Stop if encountering special block start
                if (
                    next_trimmed.startswith(("#", "```", "$$", ">"))
                    or is_table_row(next_trimmed)
                    or is_list_item(next_trimmed)[0]
                ):
                    break
                para_lines.append(next_trimmed)
                raw_para.append(lines[i])
                i += 1

            full_para = " ".join(para_lines).strip()

            if in_references_section:
                elem_type = DocumentElementType.REFERENCE_ITEM
            elif re.match(r"^Abstract\b", full_para, re.IGNORECASE) and len(full_para) < 20:
                elem_type = DocumentElementType.ABSTRACT
            else:
                elem_type = DocumentElementType.PARAGRAPH

            elements.append(
                DocumentElement(
                    id=str(uuid.uuid4())[:8],
                    type=elem_type,
                    content=full_para,
                    raw_content="\n".join(raw_para),
                    entities=extract_inline_entities(full_para),
                )
            )

        return elements

    def build_document_model(self, elements: List[DocumentElement]) -> DocumentStructure:
        """Assembles elements into complete internal DocumentStructure model."""
        title: Optional[str] = None
        abstract: Optional[str] = None
        references: List[str] = []

        total_words = 0
        total_chars = 0
        para_count = 0
        heading_count = 0
        table_count = 0
        math_count = 0
        citation_count = 0

        for elem in elements:
            if elem.type == DocumentElementType.TITLE and not title:
                title = elem.content
            elif elem.type == DocumentElementType.HEADING:
                heading_count += 1
            elif elem.type == DocumentElementType.PARAGRAPH:
                para_count += 1
            elif elem.type == DocumentElementType.ABSTRACT:
                abstract = elem.content
            elif elem.type == DocumentElementType.TABLE:
                table_count += 1
            elif elem.type == DocumentElementType.MATH_BLOCK:
                math_count += 1
            elif elem.type == DocumentElementType.REFERENCE_ITEM:
                references.append(elem.content)

            # Accumulate text metrics
            words = len(elem.content.split())
            total_words += words
            total_chars += len(elem.content)

            # Accumulate entity metrics
            for ent in elem.entities:
                if ent.entity_type == EntityType.CITATION_REFERENCE:
                    citation_count += 1
                elif ent.entity_type in (EntityType.INLINE_MATH, EntityType.DISPLAY_MATH):
                    math_count += 1

        stats = DocumentStats(
            word_count=total_words,
            character_count=total_chars,
            reading_time_minutes=round(total_words / 225.0, 1),  # standard 225 wpm academic reading rate
            paragraph_count=para_count,
            heading_count=heading_count,
            table_count=table_count,
            math_block_count=math_count,
            citation_count=citation_count,
            reference_count=len(references),
        )

        return DocumentStructure(
            title=title,
            abstract=abstract,
            elements=elements,
            stats=stats,
            references=references,
        )
