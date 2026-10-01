"""Exam Questions Skill.

Detects, validates, and structures academic examination papers, quizzes, and problem sets:
- Standardizes Question headers ('Question 1:', 'Problem 2:', 'Q3.')
- Formats multiple-choice options ((A), (B), (C), (D)) with consistent indentation
- Formats point allocations ('[5 points]', '[10 pts]')
- Standardizes Answer Key / Rubric sections
"""

import re
import time
from typing import Any, Dict, List, Optional
from backend.skills.base import BaseSkill, SkillExecutionResult, SkillValidationResult


class ExamQuestionsSkill(BaseSkill):
    """Processes academic exam questions, multiple choice options, and scoring points."""

    @property
    def id(self) -> str:
        return "exam_questions"

    @property
    def name(self) -> str:
        return "Exam Questions"

    @property
    def description(self) -> str:
        return "Standardizes exam questions, multiple-choice options ((A)-(D)), and point allocations."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 60

    @property
    def category(self) -> str:
        return "academic"

    QUESTION_HEADER_PATTERN = re.compile(
        r"^(?:#{1,4}\s+)?(?:Question|Problem|Q)\s*(\d+)[:.]?\s*(.*?)$",
        re.IGNORECASE | re.MULTILINE
    )
    OPTION_PATTERN = re.compile(r"^\s*(?:[A-Da-d]\)|\([A-Da-d]\)|[A-Da-d]\.)\s+(.*?)$", re.MULTILINE)

    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillValidationResult:
        issues: List[str] = []
        features: List[str] = []

        questions = self.QUESTION_HEADER_PATTERN.findall(text)
        options = self.OPTION_PATTERN.findall(text)

        if questions:
            features.append(f"{len(questions)}_questions_detected")
        if options:
            features.append(f"{len(options)}_mcq_options_detected")

        # Check for point values
        points = re.findall(r"\[\s*(\d+)\s*(?:points?|pts?)\s*\]", text, re.IGNORECASE)
        if points:
            features.append("point_allocations")

        return SkillValidationResult(
            is_valid=True,
            issues=issues,
            detected_features=features,
            confidence_score=1.0,
            metrics={"question_count": len(questions), "option_count": len(options)},
        )

    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        start_time = time.time()
        diagnostics: List[str] = []
        original_text = text

        lines = text.split("\n")
        output_lines: List[str] = []
        questions_formatted = 0

        for line in lines:
            stripped = line.strip()

            # 1. Standardize Question header: "Q1: text" -> "### Question 1: text"
            q_match = re.match(r"^(?:#{1,4}\s*)?(?:Question|Problem|Q)\s*(\d+)[:.]?\s*(.*)$", stripped, re.IGNORECASE)
            if q_match:
                q_num = q_match.group(1)
                q_rest = q_match.group(2).strip()
                # Format point tag in header if present
                q_rest = re.sub(r"[\(\[]\s*(\d+)\s*(?:points?|pts?)\s*[\)\]]", r"[\1 points]", q_rest, flags=re.IGNORECASE)
                output_lines.append(f"### Question {q_num}: {q_rest}" if q_rest else f"### Question {q_num}")
                questions_formatted += 1
                continue

            # 2. Standardize multiple choice options to: "  (A) Option text"
            opt_match = re.match(r"^\s*(?:([A-Da-d])\)|\(([A-Da-d])\)|([A-Da-d])\.)\s+(.*)$", stripped)
            if opt_match:
                letter = (opt_match.group(1) or opt_match.group(2) or opt_match.group(3)).upper()
                opt_text = opt_match.group(4).strip()
                output_lines.append(f"  ({letter}) {opt_text}")
                continue

            # 3. Standardize point tags: "(5 pts)" -> "[5 points]"
            pt_line = re.sub(r"[\(\[]\s*(\d+)\s*(?:points?|pts?)\s*[\)\]]", r"[\1 points]", stripped, flags=re.IGNORECASE)
            output_lines.append(pt_line)

        processed = "\n".join(output_lines)
        duration = (time.time() - start_time) * 1000.0
        is_modified = processed != original_text

        if questions_formatted > 0:
            diagnostics.append(f"Formatted and aligned {questions_formatted} exam question(s) and options.")

        return SkillExecutionResult(
            skill_id=self.id,
            skill_name=self.name,
            version=self.version,
            modified=is_modified,
            text=processed,
            diagnostics=diagnostics,
            metadata={"questions_formatted": questions_formatted},
            execution_time_ms=round(duration, 2),
        )
