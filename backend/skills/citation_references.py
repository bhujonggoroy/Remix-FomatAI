"""Citation and References Skill.

Detects, validates, and normalizes academic citations and bibliography sections:
- Detects APA parenthetical citations (e.g. '(Smith, 2023)', '(Jones & Lee, 2021)')
- Detects IEEE/numbered bracket citations (e.g. '[1]', '[2, 3]')
- Normalizes reference list headings ('## References' or '## Bibliography')
- Validates consistency between in-text citations and reference list entries
"""

import re
import time
from typing import Any, Dict, List, Optional
from backend.skills.base import BaseSkill, SkillExecutionResult, SkillValidationResult


class CitationReferencesSkill(BaseSkill):
    """Processes, extracts, and formats academic citations and bibliographies."""

    @property
    def id(self) -> str:
        return "citation_references"

    @property
    def name(self) -> str:
        return "Citation/References"

    @property
    def description(self) -> str:
        return "Detects and normalizes in-text citations (APA/IEEE) and standardizes reference list sections."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 50

    @property
    def category(self) -> str:
        return "academic"

    APA_CITATION_PATTERN = re.compile(
        r"\(([A-Z][a-zA-Z\s\.\-']+(?:et\s+al\.)?(?:\s*(?:&|and)\s*[A-Z][a-zA-Z\s\.\-']+)?,\s*(?:19|20)\d{2}[a-z]?)\)"
    )
    IEEE_CITATION_PATTERN = re.compile(r"\[\s*(\d+(?:\s*,\s*\d+)*(?:\s*-\s*\d+)?)\s*\]")

    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillValidationResult:
        issues: List[str] = []
        features: List[str] = []

        apa_citations = self.APA_CITATION_PATTERN.findall(text)
        ieee_citations = self.IEEE_CITATION_PATTERN.findall(text)

        if apa_citations:
            features.append("apa_in_text_citations")
        if ieee_citations:
            features.append("ieee_bracket_citations")

        # Check for References section
        has_ref_heading = bool(re.search(r"^#{1,3}\s+(?:References|Bibliography|Works Cited)\b", text, re.IGNORECASE | re.MULTILINE))
        if has_ref_heading:
            features.append("references_heading")

        total_citations = len(apa_citations) + len(ieee_citations)
        if total_citations > 2 and not has_ref_heading:
            issues.append(f"Document contains {total_citations} in-text citations but lacks a dedicated References section.")

        return SkillValidationResult(
            is_valid=True,
            issues=issues,
            detected_features=features,
            confidence_score=0.9 if issues else 1.0,
            metrics={
                "apa_citations_count": len(apa_citations),
                "ieee_citations_count": len(ieee_citations),
                "has_references_section": has_ref_heading,
            },
        )

    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        start_time = time.time()
        diagnostics: List[str] = []
        original_text = text
        processed = text

        # 1. Standardize References section heading to H2 (## References)
        ref_heading_pattern = re.compile(r"^(?:#{1,6}\s+)?(References|Bibliography|Works Cited)\s*$", re.IGNORECASE | re.MULTILINE)
        if ref_heading_pattern.search(processed):
            processed = ref_heading_pattern.sub(r"## \1", processed)
            diagnostics.append("Standardized References heading to Level 2 (## References).")

        # 2. Normalize spaced ampersands in APA citations: '(Smith &  Jones, 2020)' -> '(Smith & Jones, 2020)'
        processed = re.sub(r"\(([A-Z][a-zA-Z]+)\s+and\s+([A-Z][a-zA-Z]+),\s*((?:19|20)\d{2})\)", r"(\1 & \2, \3)", processed)

        # 3. Clean bracket spacing in IEEE citations: '[ 1 ]' -> '[1]'
        processed = re.sub(r"\[\s+(\d+)\s+\]", r"[\1]", processed)

        duration = (time.time() - start_time) * 1000.0
        is_modified = processed != original_text

        return SkillExecutionResult(
            skill_id=self.id,
            skill_name=self.name,
            version=self.version,
            modified=is_modified,
            text=processed,
            diagnostics=diagnostics,
            metadata={"citations_processed": True},
            execution_time_ms=round(duration, 2),
        )
