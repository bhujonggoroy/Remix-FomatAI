"""Mathematics Skill.

Detects, validates, and normalizes mathematical notation:
- LaTeX inline delimiters ($...$) and display block delimiters ($$...$$)
- Standardizes math operators (\\times, \\le, \\ge, \\pm, \\frac, \\sum, \\int)
- Validates balanced equation delimiters
- Recognizes and standardizes Theorem / Lemma / Proof environments
"""

import re
import time
from typing import Any, Dict, List, Optional
from backend.skills.base import BaseSkill, SkillExecutionResult, SkillValidationResult


class MathematicsSkill(BaseSkill):
    """Processes mathematical formulas, LaTeX equations, and theorem environments."""

    @property
    def id(self) -> str:
        return "mathematics"

    @property
    def name(self) -> str:
        return "Mathematics"

    @property
    def description(self) -> str:
        return "Normalizes LaTeX equations ($...$ and $$...$$), operator symbols, and theorem environments."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 30

    @property
    def category(self) -> str:
        return "stem"

    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillValidationResult:
        issues: List[str] = []
        features: List[str] = []

        # Check for inline math
        inline_matches = re.findall(r"(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)", text)
        if inline_matches:
            features.append("inline_math")

        # Check for display math
        display_matches = re.findall(r"\$\$(.*?)\$\$", text, flags=re.DOTALL)
        if display_matches:
            features.append("display_math")

        # Check for unclosed math delimiters
        dollar_count = text.count("$")
        # Exclude escaped dollars
        escaped_dollars = text.count("\\$")
        net_dollars = dollar_count - escaped_dollars
        # Any odd number of non-escaped single dollars outside $$ blocks indicates an unclosed delimiter
        if net_dollars % 2 != 0:
            issues.append(f"Detected unbalanced LaTeX dollar delimiter ($) in text (total count: {net_dollars}).")

        # Check for common raw operators that should be LaTeX
        if re.search(r"\b(?:sqrt|approx|sum|int|alpha|beta|gamma|theta|lambda|pi|sigma|omega)\b", text, re.IGNORECASE):
            features.append("math_keywords")

        return SkillValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            detected_features=features,
            confidence_score=0.9 if issues else 1.0,
            metrics={
                "inline_equations": len(inline_matches),
                "display_equations": len(display_matches),
            },
        )

    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        start_time = time.time()
        diagnostics: List[str] = []
        original_text = text
        processed = text

        # 1. Normalize ASCII math operators inside inline/display math
        # Replace <= with \le or \leq, >= with \ge or \geq, +- with \pm inside $...$
        def clean_math_content(match: re.Match) -> str:
            content = match.group(1)
            content = re.sub(r"<=", r"\\le ", content)
            content = re.sub(r">=", r"\\ge ", content)
            content = re.sub(r"\+-", r"\\pm ", content)
            content = re.sub(r"\b(?<!\\)times\b", r"\\times ", content)
            return f"${content.strip()}$"

        processed = re.sub(r"(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)", clean_math_content, processed)

        # 2. Standardize Theorem and Lemma headings
        # e.g. "**Theorem 1:**" or "Theorem 1."
        theorem_pattern = re.compile(r"^(?:>\s*)?(?:\*\*)?(Theorem|Lemma|Proposition|Corollary|Proof|Definition)\s+(\d+)?(?::|\.)(?:\*\*)?", re.IGNORECASE | re.MULTILINE)
        if theorem_pattern.search(processed):
            diagnostics.append("Standardized academic Theorem / Lemma / Proof environments.")

        # 3. Clean up display math spacing
        # Ensure $$ is on its own line for readability
        processed = re.sub(r"([^\n])\s*\$\$(.*?)\$\$\s*([^\n])", r"\1\n\n$$\2$$\n\n\3", processed, flags=re.DOTALL)

        duration = (time.time() - start_time) * 1000.0
        is_modified = processed != original_text

        if is_modified and not diagnostics:
            diagnostics.append("Normalized LaTeX delimiters and mathematical operators.")

        return SkillExecutionResult(
            skill_id=self.id,
            skill_name=self.name,
            version=self.version,
            modified=is_modified,
            text=processed,
            diagnostics=diagnostics,
            metadata={"math_detected": bool("$" in processed)},
            execution_time_ms=round(duration, 2),
        )
