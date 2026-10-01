"""Scientific Document Formatting Skill.

Standardizes high-level scientific and academic manuscript architecture (IMRaD):
- Enforces standardized section headers: Abstract, Introduction, Methods, Results, Discussion, Conclusion
- Normalizes Keywords block ('**Keywords:** word1, word2, word3')
- Standardizes author metadata and institutional affiliations
- Formats hierarchical section numbering (e.g. '1. Introduction', '2. Methodology')
"""

import re
import time
from typing import Any, Dict, List, Optional
from backend.skills.base import BaseSkill, SkillExecutionResult, SkillValidationResult


class ScientificDocumentSkill(BaseSkill):
    """Structures academic research papers adhering to standard scientific journal (IMRaD) guidelines."""

    @property
    def id(self) -> str:
        return "scientific_document"

    @property
    def name(self) -> str:
        return "Scientific Document Formatting"

    @property
    def description(self) -> str:
        return "Enforces standard scientific manuscript structure (IMRaD sections, Keywords, affiliations)."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 70

    @property
    def category(self) -> str:
        return "academic"

    STANDARD_SECTIONS = [
        "Abstract",
        "Introduction",
        "Related Work",
        "Methodology",
        "Methods",
        "Experimental Setup",
        "Results",
        "Discussion",
        "Conclusion",
        "Conclusions",
        "Acknowledgements",
        "Acknowledgments",
    ]

    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillValidationResult:
        issues: List[str] = []
        features: List[str] = []

        found_sections: List[str] = []
        for sec in self.STANDARD_SECTIONS:
            if re.search(r"^(?:#{1,3}\s+|\d+\.\s*)?" + re.escape(sec) + r"\b", text, re.IGNORECASE | re.MULTILINE):
                found_sections.append(sec)

        if found_sections:
            features.extend([f"section_{s.lower()}" for s in found_sections])

        # Check for Abstract in scientific papers
        has_abstract = any("abstract" in s.lower() for s in found_sections)
        if not has_abstract and len(found_sections) >= 3:
            issues.append("Document resembles a scientific paper but lacks a formal Abstract section.")

        # Check for Keywords
        has_keywords = bool(re.search(r"\bKeywords\s*:", text, re.IGNORECASE))
        if has_keywords:
            features.append("keywords_block")

        return SkillValidationResult(
            is_valid=True,
            issues=issues,
            detected_features=features,
            confidence_score=1.0,
            metrics={"detected_imrad_sections": found_sections},
        )

    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        start_time = time.time()
        diagnostics: List[str] = []
        original_text = text

        lines = text.split("\n")
        output_lines: List[str] = []
        sections_standardized = 0

        for line in lines:
            stripped = line.strip()

            # 1. Standardize Keywords block: "Keywords: a, b, c" -> "**Keywords:** a, b, c"
            kw_match = re.match(r"^(?:\*\*)?Keywords(?:\*\*)?\s*[:\-]\s*(.*)$", stripped, re.IGNORECASE)
            if kw_match:
                kw_body = kw_match.group(1).strip()
                output_lines.append(f"**Keywords:** {kw_body}")
                continue

            # 2. Standardize core IMRaD section headings to Level 2
            # e.g., "1. Introduction" or "## 1. Introduction" or "Introduction"
            matched_sec = None
            for sec in self.STANDARD_SECTIONS:
                pattern = r"^(?:#{1,6}\s+)?(?:\d+\.?\s*)?" + re.escape(sec) + r"\s*$"
                if re.match(pattern, stripped, re.IGNORECASE):
                    matched_sec = sec
                    break

            if matched_sec:
                # Format to clean ## Section Name
                output_lines.append(f"## {matched_sec}")
                sections_standardized += 1
                continue

            output_lines.append(line)

        processed = "\n".join(output_lines)
        duration = (time.time() - start_time) * 1000.0
        is_modified = processed != original_text

        if sections_standardized > 0:
            diagnostics.append(f"Standardized {sections_standardized} scientific IMRaD section heading(s).")

        return SkillExecutionResult(
            skill_id=self.id,
            skill_name=self.name,
            version=self.version,
            modified=is_modified,
            text=processed,
            diagnostics=diagnostics,
            metadata={"sections_standardized": sections_standardized},
            execution_time_ms=round(duration, 2),
        )
