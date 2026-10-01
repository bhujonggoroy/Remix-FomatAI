"""Markdown structure parsing utilities for academic document blocks."""

import re
from typing import List, Optional, Tuple
from backend.models.document import TableColumnAlign, TableData


def parse_markdown_table(lines: List[str]) -> Optional[TableData]:
    """Parses raw lines representing a Markdown pipe table into structured TableData."""
    if len(lines) < 2:
        return None

    # Filter out empty or whitespace lines
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    if len(cleaned_lines) < 2:
        return None

    header_line = cleaned_lines[0]
    delimiter_line = cleaned_lines[1]

    # Validate delimiter line (e.g. |---|:---:|---:|)
    if not re.search(r"^\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?$", delimiter_line):
        return None

    def split_cells(line: str) -> List[str]:
        # Strip outer pipes if present
        trimmed = line.strip()
        if trimmed.startswith("|"):
            trimmed = trimmed[1:]
        if trimmed.endswith("|"):
            trimmed = trimmed[:-1]
        return [cell.strip() for cell in trimmed.split("|")]

    headers = split_cells(header_line)
    delimiters = split_cells(delimiter_line)

    alignments: List[TableColumnAlign] = []
    for d in delimiters:
        d = d.strip()
        if d.startswith(":") and d.endswith(":"):
            alignments.append(TableColumnAlign.CENTER)
        elif d.endswith(":"):
            alignments.append(TableColumnAlign.RIGHT)
        else:
            alignments.append(TableColumnAlign.LEFT)

    rows: List[List[str]] = []
    for row_line in cleaned_lines[2:]:
        if not row_line.startswith("|") and "|" not in row_line:
            continue
        cells = split_cells(row_line)
        # Pad cells if necessary
        while len(cells) < len(headers):
            cells.append("")
        rows.append(cells[: len(headers)])

    return TableData(
        headers=headers,
        rows=rows,
        alignments=alignments,
    )


def extract_heading_info(line: str) -> Optional[Tuple[int, str]]:
    """Detects Markdown heading level and stripped text.

    Returns (level, title) or None.
    """
    match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
    if match:
        level = len(match.group(1))
        title = match.group(2).strip()
        return (level, title)
    return None


def is_table_row(line: str) -> bool:
    """Checks whether a line resembles a Markdown table row."""
    trimmed = line.strip()
    return trimmed.startswith("|") and ("|" in trimmed[1:])


def is_list_item(line: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Checks whether a line is a list item.

    Returns (is_list, list_type, text). list_type is 'ordered' or 'unordered'.
    """
    trimmed = line.strip()
    # Unordered list marker: -, *, +
    unord_match = re.match(r"^[-*+]\s+(.+)$", trimmed)
    if unord_match:
        return True, "unordered", unord_match.group(1).strip()

    # Ordered list marker: 1. or 1)
    ord_match = re.match(r"^\d+[\.\)]\s+(.+)$", trimmed)
    if ord_match:
        return True, "ordered", ord_match.group(1).strip()

    return False, None, None


def is_blockquote(line: str) -> Tuple[bool, Optional[str]]:
    """Checks whether a line is a blockquote."""
    trimmed = line.strip()
    if trimmed.startswith(">"):
        content = trimmed.lstrip("> ").strip()
        return True, content
    return False, None
