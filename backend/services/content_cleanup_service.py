"""Content Cleanup Service for FormatAI.

Separates content cleanup from formatting cleanup.
Performs:
- AI conversational chatter removal (preambles & postscripts)
- Redundant and empty heading elimination
- Unnecessary/orphan bullet removal (converting narrative bullets to paragraphs)
- Fragmented AI-generated paragraph consolidation
Preserves all academic meaning and factual content.
"""

import re
from typing import List


from backend.utils.math_detector import normalize_delimiters

# Common AI chat preamble patterns
AI_PREAMBLE_PATTERNS = [
    r"^(?:sure|certainly|absolutely)[!,.]?\s*(?:here(?:\s+is|\'s)|below is|i have formatted).+?[:\n]",
    r"^here(?:\s+is|\'s)\s+(?:the|an|your)\s+(?:academic|formatted|draft|paper|article|essay|document|report).+?[:\n]",
    r"^below\s+is\s+(?:the|a)\s+(?:revised|formatted|structured|academic).+?[:\n]",
    r"^i(?:'d| would)\s+be\s+happy\s+to\s+format.+?[:\n]",
    r"^(?:as\s+requested|per\s+your\s+request)[,:]\s*",
]

# Common AI chat postscript patterns
AI_POSTSCRIPT_PATTERNS = [
    r"(?:i\s+)?hope\s+this\s+(?:helps|format(?:ting)?\s+helps|meets\s+your\s+needs)[!.]?.*$",
    r"let\s+me\s+know\s+if\s+you\s+(?:need|would\s+like)\s+(?:any\s+)?(?:further|more|changes|adjustments|edits|additions)[!.]?.*$",
    r"feel\s+free\s+to\s+(?:ask|reach\s+out)\s+if\s+you\s+need.*$",
    r"please\s+let\s+me\s+know\s+if\s+you\s+have\s+any\s+questions[!.]?.*$",
]


class ContentCleanupService:
    """Cleans academic content from structural and conversational noise."""

    def cleanup(self, raw_text: str) -> str:
        """Runs the complete content cleanup pipeline."""
        if not raw_text or not raw_text.strip():
            return ""

        # Normalize math delimiters before paragraph segmentation
        normalized = normalize_delimiters(raw_text)
        text = self.remove_ai_conversational_noise(normalized)
        lines = text.split("\n")
        lines = self.remove_redundant_headings(lines)
        lines = self.remove_unnecessary_bullets(lines)
        lines = self.consolidate_fragmented_paragraphs(lines)

        return "\n".join(lines).strip()

    def remove_ai_conversational_noise(self, text: str) -> str:
        """Strips AI conversational preambles and postscripts while preserving document body."""
        cleaned = text.strip()

        # 1. Strip preambles from beginning
        for pattern in AI_PREAMBLE_PATTERNS:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE | re.MULTILINE)
            if match and match.start() < 200:  # Only at the beginning
                cleaned = cleaned[match.end():].lstrip()

        # 2. Strip postscripts from the end
        for pattern in AI_POSTSCRIPT_PATTERNS:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE | re.MULTILINE)
            if match and match.start() > (len(cleaned) - 350):  # Only near the tail
                cleaned = cleaned[:match.start()].rstrip()

        return cleaned

    def remove_redundant_headings(self, lines: List[str]) -> List[str]:
        """Eliminates empty headings (e.g. '## ') and duplicate consecutive headings."""
        result: List[str] = []
        last_heading_text = ""

        for line in lines:
            trimmed = line.strip()

            # Detect empty heading (e.g. '##', '###   ')
            if re.match(r"^#{1,6}\s*$", trimmed):
                continue

            # Detect heading with text
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", trimmed)
            if heading_match:
                title = heading_match.group(2).strip().lower()
                # Skip duplicate heading directly following the same title
                if title == last_heading_text:
                    continue
                last_heading_text = title
                result.append(line)
            else:
                if trimmed:
                    last_heading_text = ""  # Reset when non-heading content intervenes
                result.append(line)

        return result

    def remove_unnecessary_bullets(self, lines: List[str]) -> List[str]:
        """Converts orphan bullets containing long academic narrative text into proper paragraphs."""
        result: List[str] = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            trimmed = line.strip()
            bullet_match = re.match(r"^[-*+]\s+(.+)$", trimmed)

            if bullet_match:
                content = bullet_match.group(1).strip()
                # Check if this bullet is isolated (preceded and followed by non-list lines or blank lines)
                prev_is_list = i > 0 and bool(re.match(r"^[-*+\d\.]\s+", lines[i - 1].strip()))
                next_is_list = i + 1 < n and bool(re.match(r"^[-*+\d\.]\s+", lines[i + 1].strip()))

                # If isolated and long (> 120 chars or multiple sentences), convert to paragraph
                is_isolated = not prev_is_list and not next_is_list
                is_narrative = len(content) > 120 or content.count(". ") >= 1

                if is_isolated and is_narrative:
                    result.append(content)
                else:
                    result.append(line)
            else:
                result.append(line)
            i += 1

        return result

    def consolidate_fragmented_paragraphs(self, lines: List[str]) -> List[str]:
        """Merges fragmented 1-sentence paragraphs that are part of the same conceptual discourse.

        Preserves code blocks, tables, math blocks, headings, and lists intact.
        """
        result: List[str] = []
        i = 0
        n = len(lines)
        in_code_or_math = False

        while i < n:
            line = lines[i]
            trimmed = line.strip()

            # Track fenced blocks
            if trimmed.startswith("```") or trimmed.startswith("$$"):
                in_code_or_math = not in_code_or_math
                result.append(line)
                i += 1
                continue

            if in_code_or_math:
                result.append(line)
                i += 1
                continue

            # Check if this line is an incomplete sentence or fragmented paragraph candidate
            # e.g., line doesn't end with terminal punctuation (. ? ! :) or ends with a comma/conjunction
            # and next line is another fragment
            if (
                trimmed
                and not trimmed.startswith("#")
                and not trimmed.startswith("|")
                and not trimmed.startswith(">")
                and not re.match(r"^[-*+\d]+[\.\)]\s+", trimmed)
                and i + 2 < n
                and lines[i + 1].strip() == ""  # blank line separator
            ):
                next_line = lines[i + 2].strip()
                # If current line ends with comma or lowercase or starts with continuation
                # or is very short fragment (< 60 chars) without terminal period:
                if (
                    not trimmed.endswith((".", "?", "!", ":", ";", '"', "”"))
                    and next_line
                    and not next_line.startswith(("#", "|", ">", "-", "*", "+", "`", "$"))
                    and not re.match(r"^\d+[\.\)]\s+", next_line)
                ):
                    # Merge current line and next line
                    result.append(f"{trimmed} {next_line}")
                    i += 3
                    continue

            result.append(line)
            i += 1

        return result
