"""Statistics Skill.

Standardizes empirical and statistical results reporting to academic conventions:
- Formats p-values (e.g. 'p < .05', 'p = .002', removes leading zero as p cannot exceed 1.0)
- Italicizes standard statistical test symbols (*p*, *t*, *F*, *r*, *z*, *M*, *SD*, *N*, *df*)
- Normalizes confidence intervals: '95% CI [lower, upper]'
- Standardizes test statistics notation (e.g. 't(24) = 2.34', 'F(1, 48) = 4.12')
"""

import re
import time
from typing import Any, Dict, List, Optional
from backend.skills.base import BaseSkill, SkillExecutionResult, SkillValidationResult


class StatisticsSkill(BaseSkill):
    """Processes and standardizes quantitative empirical results and statistical notations."""

    @property
    def id(self) -> str:
        return "statistics"

    @property
    def name(self) -> str:
        return "Statistics"

    @property
    def description(self) -> str:
        return "Standardizes statistical reporting (APA-compliant p-values, *t*/*F*/*r* notation, and confidence intervals)."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 35

    @property
    def category(self) -> str:
        return "stem"

    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillValidationResult:
        issues: List[str] = []
        features: List[str] = []

        # Detect p-values with leading zero (e.g. p = 0.05 instead of p = .05)
        if re.search(r"\bp\s*[=<]\s*0\.\d+", text):
            issues.append("Found p-values with non-standard leading zero (academic convention uses 'p < .05' or 'p = .02').")
            features.append("p_value_leading_zero")

        # Detect statistical tests
        if re.search(r"\b[tFzr]\s*\(\s*\d+\s*(?:,\s*\d+)?\s*\)\s*=", text):
            features.append("test_statistic")

        # Detect confidence intervals
        if re.search(r"\bCI\b", text, re.IGNORECASE):
            features.append("confidence_interval")

        # Detect descriptive statistics
        if re.search(r"\b(?:M|SD|SE|IQR)\s*=", text):
            features.append("descriptive_statistics")

        return SkillValidationResult(
            is_valid=True,
            issues=issues,
            detected_features=features,
            confidence_score=0.95 if issues else 1.0,
            metrics={"features_count": len(features)},
        )

    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        start_time = time.time()
        diagnostics: List[str] = []
        original_text = text
        processed = text

        # 1. Normalize p-values: strip leading zero (p = 0.04 -> *p* = .04)
        def normalize_p_value(match: re.Match) -> str:
            op = match.group(1)
            val = match.group(2)
            # Remove leading zero
            norm_val = val.lstrip("0") if val.startswith("0.") else val
            return f"*p* {op} {norm_val}"

        p_pattern = re.compile(r"\b(?:(?:\*p\*)|p)\s*([=<><=]+)\s*(0?\.\d+)\b", re.IGNORECASE)
        processed = p_pattern.sub(normalize_p_value, processed)

        # 2. Italicize standard statistical test symbols when followed by test parameters
        # t(df) = ... -> *t*(df) = ...
        # F(df1, df2) = ... -> *F*(df1, df2) = ...
        test_pattern = re.compile(r"\b(?<!\*)([tFrz])\s*(\(\s*\d+(?:\s*,\s*\d+)?\s*\)\s*=\s*-?\d+(?:\.\d+)?)\b")
        processed = test_pattern.sub(r"*\1*\2", processed)

        # 3. Italicize descriptive statistics: M = ..., SD = ...
        desc_pattern = re.compile(r"\b(?<!\*)(M|SD|SE)\s*=\s*(-?\d+(?:\.\d+)?)\b")
        processed = desc_pattern.sub(r"*\1* = \2", processed)

        # 4. Standardize Confidence Intervals: CI = [...] or 95% CI: ... -> 95% CI [x, y]
        ci_pattern = re.compile(r"\b(?:(\d{2}%)\s*)?CI\s*[:=]?\s*\[?\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]?", re.IGNORECASE)
        processed = ci_pattern.sub(lambda m: f"{m.group(1) or '95%'} CI [{m.group(2)}, {m.group(3)}]", processed)

        duration = (time.time() - start_time) * 1000.0
        is_modified = processed != original_text

        if is_modified:
            diagnostics.append("Standardized statistical notation, p-values, and confidence intervals to academic standards.")

        return SkillExecutionResult(
            skill_id=self.id,
            skill_name=self.name,
            version=self.version,
            modified=is_modified,
            text=processed,
            diagnostics=diagnostics,
            metadata={"statistical_elements_normalized": is_modified},
            execution_time_ms=round(duration, 2),
        )
