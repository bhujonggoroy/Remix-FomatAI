"""Markdown Cleanup Skill.

Performs robust pre-processing cleanup:
- Strips conversational AI preamble and chatter ("Here is your paper", "Sure! I can help...")
- Normalizes excessive blank lines and trailing whitespace
- Fixes broken markdown bold/italic tags and orphan bullet markers
"""

import re
import time
from typing import Any, Dict, List, Optional
from backend.skills.base import BaseSkill, SkillExecutionResult, SkillValidationResult


class MarkdownCleanupSkill(BaseSkill):
    """Cleans up raw markdown, stripping conversational noise and normalizing syntax."""

    @property
    def id(self) -> str:
        return "markdown_cleanup"

    @property
    def name(self) -> str:
        return "Markdown Cleanup"

    @property
    def description(self) -> str:
        return "Removes conversational AI prefixes, fixes orphan list markers, and standardizes whitespace."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 10  # Pre-processing priority: runs first

    @property
    def category(self) -> str:
        return "editorial"

    # Conversational chat prefixes commonly emitted by LLMs
    CHAT_PATTERNS = [
        re.compile(r"^(?:sure(?: thing)?|certainly|here is|here's|below is|of course)[^:\n]*:\s*", re.IGNORECASE),
        re.compile(r"^(?:as requested|i have formatted|i've prepared|hope this helps)[^:\n]*:\s*", re.IGNORECASE),
        re.compile(r"^(?:let me know if you need anything else|hope this helps!).*$", re.IGNORECASE | re.MULTILINE),
    ]

    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillValidationResult:
        issues: List[str] = []
        features: List[str] = []

        if not text or not text.strip():
            return SkillValidationResult(is_valid=False, issues=["Text is empty."])

        # Check for chat prefixes
        has_chat = any(p.search(text) for p in self.CHAT_PATTERNS)
        if has_chat:
            features.append("conversational_preamble")
            issues.append("Contains conversational chatbot preamble.")

        # Check for excessive blank lines
        if re.search(r"\n{4,}", text):
            features.append("excessive_blank_lines")

        # Check for trailing whitespace
        if re.search(r"[ \t]+$", text, re.MULTILINE):
            features.append("trailing_whitespace")

        return SkillValidationResult(
            is_valid=True,
            issues=issues,
            detected_features=features,
            confidence_score=0.95 if features else 1.0,
            metrics={"char_count": len(text)},
        )

    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        start_time = time.time()
        diagnostics: List[str] = []
        original_text = text

        cleaned = text

        # 1. Strip conversational chatter
        for pattern in self.CHAT_PATTERNS:
            subbed = pattern.sub("", cleaned)
            if subbed != cleaned:
                diagnostics.append("Stripped conversational chatbot boilerplate.")
                cleaned = subbed

        # 2. Trim trailing whitespace per line
        cleaned = re.sub(r"[ \t]+$", "", cleaned, flags=re.MULTILINE)

        # 3. Collapse 3+ consecutive blank lines to standard 2 blank lines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # 4. Fix orphan bullet points (e.g. lone '-' or '*' without text)
        cleaned = re.sub(r"^[ \t]*[-*+][ \t]*$", "", cleaned, flags=re.MULTILINE)

        # 5. Fix malformed bold markers with spaces inside (e.g. '** text **' -> '**text**')
        cleaned = re.sub(r"\*\*[ \t]+([^\*\n]+?)[ \t]+\*\*", r"**\1**", cleaned)

        duration = (time.time() - start_time) * 1000.0
        is_modified = cleaned != original_text

        if is_modified and not diagnostics:
            diagnostics.append("Standardized markdown whitespace and list markers.")

        return SkillExecutionResult(
            skill_id=self.id,
            skill_name=self.name,
            version=self.version,
            modified=is_modified,
            text=cleaned.strip(),
            diagnostics=diagnostics,
            metadata={"original_length": len(original_text), "cleaned_length": len(cleaned)},
            execution_time_ms=round(duration, 2),
        )
