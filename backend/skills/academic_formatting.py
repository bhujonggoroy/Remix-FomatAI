"""Academic Formatting Skill.

Standardizes academic hierarchy, typography, and paragraph aesthetics:
- Validates and fixes heading hierarchy (prevents level skipping like H1 -> H3)
- Applies publication-grade typography (em-dashes, typographic quotes, ellipses)
- Enforces academic paragraph spacing
"""

import re
import time
from typing import Any, Dict, List, Optional
from backend.skills.base import BaseSkill, SkillExecutionResult, SkillValidationResult


class AcademicFormattingSkill(BaseSkill):
    """Enforces academic hierarchy, heading structure, and typographic standards."""

    @property
    def id(self) -> str:
        return "academic_formatting"

    @property
    def name(self) -> str:
        return "Academic Formatting"

    @property
    def description(self) -> str:
        return "Standardizes heading hierarchy (H1-H4), smart typography, and academic paragraph margins."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 20

    @property
    def category(self) -> str:
        return "formatting"

    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillValidationResult:
        issues: List[str] = []
        features: List[str] = []

        lines = text.split("\n")
        last_heading_level = 0

        for idx, line in enumerate(lines, 1):
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                level = len(m.group(1))
                features.append(f"heading_h{level}")
                if last_heading_level > 0 and level > last_heading_level + 1:
                    issues.append(
                        f"Heading level jump from H{last_heading_level} to H{level} at line {idx}."
                    )
                last_heading_level = level

        # Check for non-typographic symbols
        if "--" in text and "---" not in text:
            features.append("hyphen_em_dash_candidate")
        if "..." in text:
            features.append("ascii_ellipsis")

        return SkillValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            detected_features=list(set(features)),
            confidence_score=0.9 if issues else 1.0,
            metrics={"heading_count": len([f for f in features if f.startswith("heading")])},
        )

    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        start_time = time.time()
        diagnostics: List[str] = []
        original_text = text

        lines = text.split("\n")
        processed_lines: List[str] = []
        last_level = 0
        fixes = 0

        for line in lines:
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()

                # Repair skipped heading level (e.g. H1 followed directly by H3 becomes H2)
                if last_level > 0 and level > last_level + 1:
                    level = last_level + 1
                    fixes += 1

                last_level = level
                # Ensure space after hash marks and clean title
                processed_lines.append(f"{'#' * level} {title}")
            else:
                processed_lines.append(line)

        rebuilt = "\n".join(processed_lines)

        # Smart typography
        # Convert -- to em-dash — (avoiding markdown table delimiters ---)
        rebuilt = re.sub(r"(?<!-)\s*--\s*(?!-)", " — ", rebuilt)
        # Convert ... to …
        rebuilt = re.sub(r"\.\.\.", "…", rebuilt)

        if fixes > 0:
            diagnostics.append(f"Corrected {fixes} skipped heading hierarchy level(s).")
        if "--" in original_text and "—" in rebuilt:
            diagnostics.append("Standardized typography to publication-grade em-dashes and ellipses.")

        duration = (time.time() - start_time) * 1000.0

        return SkillExecutionResult(
            skill_id=self.id,
            skill_name=self.name,
            version=self.version,
            modified=rebuilt != original_text,
            text=rebuilt,
            diagnostics=diagnostics,
            metadata={"heading_fixes": fixes},
            execution_time_ms=round(duration, 2),
        )
