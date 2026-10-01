"""Formatting Cleanup Service for FormatAI.

Separates formatting rules from content cleanup.
Performs:
- Heading hierarchy repair (contiguous monotonic levels H1 -> H2 -> H3)
- Spacing normalization
- List marker and ordered numbering normalization
- Typography normalization (smart quotes, em-dashes, en-dashes, ellipses)
- Mathematical expression delimiter validation
- Removal of broken markdown formatting artifacts
"""

import re
from typing import List, Tuple
from backend.utils.text_processing import normalize_academic_typography


class FormattingService:
    """Enforces strict academic formatting rules on textual content."""

    def format_document(
        self,
        text: str,
        apply_typography: bool = True,
    ) -> Tuple[str, List[str]]:
        """Applies formatting rules and returns (formatted_text, diagnostics_log)."""
        if not text or not text.strip():
            return "", []

        diagnostics: List[str] = []

        # 1. Remove broken formatting artifacts
        cleaned_text, artifact_diag = self.remove_broken_formatting_artifacts(text)
        diagnostics.extend(artifact_diag)

        # 2. Fix mathematical representations
        cleaned_text, math_diag = self.fix_mathematical_representation(cleaned_text)
        diagnostics.extend(math_diag)

        # 3. Line-by-line formatting
        lines = cleaned_text.split("\n")

        # 4. Fix heading hierarchy
        lines, hierarchy_diag = self.fix_heading_hierarchy(lines)
        diagnostics.extend(hierarchy_diag)

        # 5. Normalize lists
        lines, list_diag = self.normalize_lists(lines)
        diagnostics.extend(list_diag)

        # 6. Normalize spacing
        text = "\n".join(lines)
        text = self.normalize_spacing(text)

        # 7. Normalize typography
        if apply_typography:
            text = normalize_academic_typography(text)
            diagnostics.append("Normalized academic typography (smart quotes, dashes, ellipses).")

        return text, diagnostics

    def fix_heading_hierarchy(self, lines: List[str]) -> Tuple[List[str], List[str]]:
        """Normalizes broken heading leaps (e.g. # to ###) into contiguous academic levels."""
        diagnostics: List[str] = []
        result: List[str] = []

        # First pass: collect all heading levels
        original_levels: List[int] = []
        for line in lines:
            m = re.match(r"^(#{1,6})\s+", line.strip())
            if m:
                original_levels.append(len(m.group(1)))

        if not original_levels:
            return lines, []

        # Map disconnected levels to monotonic contiguous sequence
        # e.g. [1, 3, 4] -> 1:1, 3:2, 4:3
        sorted_unique = sorted(list(set(original_levels)))
        level_map = {lvl: i + 1 for i, lvl in enumerate(sorted_unique)}

        has_jumps = any(level_map[orig] != orig for orig in original_levels)
        if has_jumps:
            diagnostics.append("Repaired non-contiguous heading hierarchy levels to standard contiguous depth.")

        # Second pass: apply mapping
        for line in lines:
            m = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if m:
                orig_lvl = len(m.group(1))
                new_lvl = level_map[orig_lvl]
                title = m.group(2).strip()
                result.append(f"{'#' * new_lvl} {title}")
            else:
                result.append(line)

        return result, diagnostics

    def normalize_spacing(self, text: str) -> str:
        """Collapses excessive vertical blank lines to at most one, and trims trailing line whitespace."""
        # Normalize carriage returns
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Trim trailing spaces on each line
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Collapse 3+ newlines to 2 newlines (single empty line)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Ensure headings have proper breathing room
        text = re.sub(r"([^\n])\n(#{1,6}\s+)", r"\1\n\n\2", text)

        # Ensure display math blocks have blank lines around them
        text = re.sub(r"([^\n])\n(\$\$\b|\$\$\n)", r"\1\n\n\2", text)
        text = re.sub(r"(\n\$\$)\n([^\n])", r"\1\n\n\2", text)

        return text.strip()

    def normalize_lists(self, lines: List[str]) -> Tuple[List[str], List[str]]:
        """Standardizes list item bullet characters and repairs broken sequential numbering."""
        diagnostics: List[str] = []
        result: List[str] = []
        in_ordered_list = False
        current_ordered_num = 1
        fixed_numbering = False

        for line in lines:
            trimmed = line.strip()

            # Unordered list: convert * or + to -
            unord_match = re.match(r"^([*+])\s+(.+)$", trimmed)
            if unord_match:
                in_ordered_list = False
                result.append(f"- {unord_match.group(2)}")
                continue

            # Standard dash bullet
            if re.match(r"^-\s+(.+)$", trimmed):
                in_ordered_list = False
                result.append(line)
                continue

            # Ordered list: check numbering sequence
            ord_match = re.match(r"^(\d+)[\.\)]\s+(.+)$", trimmed)
            if ord_match:
                content = ord_match.group(2)
                if not in_ordered_list:
                    in_ordered_list = True
                    current_ordered_num = 1
                else:
                    current_ordered_num += 1

                actual_num = int(ord_match.group(1))
                if actual_num != current_ordered_num:
                    fixed_numbering = True

                result.append(f"{current_ordered_num}. {content}")
                continue

            # Non-list line
            if not trimmed:
                result.append(line)
            else:
                in_ordered_list = False
                result.append(line)

        if fixed_numbering:
            diagnostics.append("Renumbered broken or non-sequential ordered list items.")

        return result, diagnostics

    def fix_mathematical_representation(self, text: str) -> Tuple[str, List[str]]:
        """Ensures math environments and inline delimiters ($...$) are consistently delimited."""
        diagnostics: List[str] = []
        original = text

        # 1. Protect and normalize display math $$...$$
        # Clean multiline display math whitespace
        def clean_display_math(match):
            inner = match.group(1).strip()
            return f"\n\n$$\n{inner}\n$$\n\n"

        text = re.sub(r"(?:\n|^)\$\$\s*([^\$]+?)\s*\$\$(?:\n|$)", clean_display_math, text)

        # 2. Normalize inline math spacing within a single line (avoid matching across lines or periods)
        def clean_inline_math(match):
            inner = match.group(1).strip()
            return f"${inner}$"

        text = re.sub(r"(?<!\$)\$(?!\$)\s+([^$\n\r.!?]+?)\s+(?<!\$)\$(?!\$)", clean_inline_math, text)

        if text != original:
            diagnostics.append("Cleaned up mathematical syntax delimiters ($ and $$).")

        return text, diagnostics

    def remove_broken_formatting_artifacts(self, text: str) -> Tuple[str, List[str]]:
        """Removes orphan tags, dangling asterisks, or unclosed formatting tokens."""
        diagnostics: List[str] = []
        lines = text.split("\n")
        cleaned_lines: List[str] = []

        for line in lines:
            # Check for orphan dangling markdown symbols
            if line.strip() in ("**", "*", "__", "_", "```", "~~~", "##", "#"):
                diagnostics.append(f"Removed orphan formatting artifact: '{line.strip()}'")
                continue

            # Remove trailing lone hashes like 'Introduction #'
            cleaned = re.sub(r"\s+#+$", "", line)
            cleaned_lines.append(cleaned)

        return "\n".join(cleaned_lines), diagnostics
