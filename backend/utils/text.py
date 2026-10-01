"""Reusable text and formatting utilities."""

import re


def count_words(text: str) -> int:
    """Calculates word count of given text."""
    if not text:
        return 0
    return len(text.split())


def sanitize_raw_text(text: str) -> str:
    """Normalizes newlines and strips excessive whitespace."""
    if not text:
        return ""
    # Normalize line breaks to \n
    text = re.sub(r"\r\n|\r", "\n", text)
    # Strip trailing whitespace on lines
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()
