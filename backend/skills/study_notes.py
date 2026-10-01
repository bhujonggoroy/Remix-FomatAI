"""Study Notes Skill.

Structures educational summaries, study guides, and lecture notes:
- Formats Key Concepts and Definitions into clean blockquote callouts
- Standardizes 'Key Takeaways' and 'Summary' sections
- Organizes Cornell-style recall cues and review checkpoints
"""

import re
import time
from typing import Any, Dict, List, Optional
from backend.skills.base import BaseSkill, SkillExecutionResult, SkillValidationResult


class StudyNotesSkill(BaseSkill):
    """Processes study notes, key concept callouts, and summary takeaways."""

    @property
    def id(self) -> str:
        return "study_notes"

    @property
    def name(self) -> str:
        return "Study Notes"

    @property
    def description(self) -> str:
        return "Formats key concepts, definitions into highlighted callouts, and structures study takeaways."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 65

    @property
    def category(self) -> str:
        return "academic"

    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillValidationResult:
        issues: List[str] = []
        features: List[str] = []

        if re.search(r"\b(?:Key Takeaways?|Summary|Review Questions?|Concept Check)\b", text, re.IGNORECASE):
            features.append("study_sections")

        if re.search(r"^(?:Definition|Note|Important|Remember)[:.]", text, re.IGNORECASE | re.MULTILINE):
            features.append("unformatted_callouts")

        return SkillValidationResult(
            is_valid=True,
            issues=issues,
            detected_features=features,
            confidence_score=1.0,
            metrics={"study_features_count": len(features)},
        )

    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        start_time = time.time()
        diagnostics: List[str] = []
        original_text = text

        lines = text.split("\n")
        output_lines: List[str] = []
        callouts_formatted = 0

        for line in lines:
            stripped = line.strip()

            # 1. Convert bare definitions/notes into standard markdown callouts:
            # "Definition: text" -> "> **Definition:** text"
            # "Note: text" -> "> **Note:** text"
            callout_match = re.match(r"^(?:>\s*)?(Definition|Note|Important|Key Concept|Takeaway)[:.]\s*(.*)$", stripped, re.IGNORECASE)
            if callout_match:
                tag = callout_match.group(1).title()
                body = callout_match.group(2).strip()
                output_lines.append(f"> **{tag}:** {body}")
                callouts_formatted += 1
                continue

            # 2. Standardize Summary / Key Takeaways headings to Level 2
            if re.match(r"^(?:#{1,6}\s+)?(Key Takeaways?|Summary|Review Questions?)\s*$", stripped, re.IGNORECASE):
                section_title = stripped.lstrip("#").strip().title()
                output_lines.append(f"## {section_title}")
                continue

            output_lines.append(line)

        processed = "\n".join(output_lines)
        duration = (time.time() - start_time) * 1000.0
        is_modified = processed != original_text

        if callouts_formatted > 0:
            diagnostics.append(f"Structured {callouts_formatted} study callout(s) and key concept definitions.")

        return SkillExecutionResult(
            skill_id=self.id,
            skill_name=self.name,
            version=self.version,
            modified=is_modified,
            text=processed,
            diagnostics=diagnostics,
            metadata={"callouts_formatted": callouts_formatted},
            execution_time_ms=round(duration, 2),
        )
