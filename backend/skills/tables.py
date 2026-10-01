"""Tables Skill.

Detects, validates, and standardizes academic and Markdown tables:
- Validates column count consistency across header, delimiter, and rows
- Pads and aligns cells for clean monospace and rendered layout
- Standardizes academic Table captions (e.g. 'Table 1: Descriptive Title')
- Formats column alignment indicators (:---, :---:, ---:)
"""

import re
import time
from typing import Any, Dict, List, Optional
from backend.skills.base import BaseSkill, SkillExecutionResult, SkillValidationResult


class TablesSkill(BaseSkill):
    """Processes, validates, and aligns academic tabular structures."""

    @property
    def id(self) -> str:
        return "tables"

    @property
    def name(self) -> str:
        return "Tables"

    @property
    def description(self) -> str:
        return "Validates and standardizes academic Markdown tables, column alignments, and table captions."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 45

    @property
    def category(self) -> str:
        return "formatting"

    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillValidationResult:
        issues: List[str] = []
        features: List[str] = []

        lines = text.split("\n")
        table_count = 0
        in_table = False
        current_cols = 0

        for line_idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2:
                if not in_table:
                    in_table = True
                    table_count += 1
                    features.append(f"table_{table_count}")
                    cells = [c.strip() for c in stripped.split("|")[1:-1]]
                    current_cols = len(cells)
                else:
                    cells = [c.strip() for c in stripped.split("|")[1:-1]]
                    # Check delimiter line
                    if re.match(r"^[\s\-:|]+$", stripped):
                        if len(cells) != current_cols:
                            issues.append(
                                f"Table {table_count} delimiter has {len(cells)} columns, but header has {current_cols} (line {line_idx})."
                            )
                    else:
                        if len(cells) != current_cols:
                            issues.append(
                                f"Table {table_count} row has {len(cells)} columns, but header has {current_cols} (line {line_idx})."
                            )
            else:
                in_table = False

        # Detect table captions
        if re.search(r"^(?:Table|\*\*Table)\s+\d+[:.]", text, re.MULTILINE):
            features.append("table_caption")

        return SkillValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            detected_features=features,
            confidence_score=0.9 if issues else 1.0,
            metrics={"table_count": table_count},
        )

    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        start_time = time.time()
        diagnostics: List[str] = []
        original_text = text

        lines = text.split("\n")
        output_lines: List[str] = []
        i = 0
        tables_formatted = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Check if this line starts a table
            if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2:
                # Accumulate all consecutive table rows
                table_block: List[str] = []
                while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                    table_block.append(lines[i].strip())
                    i += 1

                if len(table_block) >= 2:
                    # Parse cells for alignment
                    parsed_rows: List[List[str]] = []
                    for row_str in table_block:
                        parsed_rows.append([c.strip() for c in row_str.split("|")[1:-1]])

                    # Compute max width per column
                    num_cols = max(len(r) for r in parsed_rows)
                    col_widths = [3] * num_cols

                    for row in parsed_rows:
                        for col_idx, cell in enumerate(row):
                            if col_idx < num_cols:
                                # For delimiter line, minimum 3 chars
                                if re.match(r"^:?-+:?$", cell):
                                    col_widths[col_idx] = max(col_widths[col_idx], len(cell))
                                else:
                                    col_widths[col_idx] = max(col_widths[col_idx], len(cell))

                    # Reconstruct aligned table
                    aligned_table: List[str] = []
                    for r_idx, row in enumerate(parsed_rows):
                        padded_cells: List[str] = []
                        for col_idx in range(num_cols):
                            cell_val = row[col_idx] if col_idx < len(row) else ""
                            target_w = col_widths[col_idx]

                            if r_idx == 1 and re.match(r"^:?-+:?$", cell_val):
                                # Rebuild delimiter
                                is_left = cell_val.startswith(":")
                                is_right = cell_val.endswith(":")
                                dashes = "-" * (target_w - (1 if is_left else 0) - (1 if is_right else 0))
                                delim_cell = f"{':' if is_left else ''}{dashes}{':' if is_right else ''}"
                                padded_cells.append(delim_cell)
                            else:
                                padded_cells.append(cell_val.ljust(target_w))

                        aligned_table.append(f"| {' | '.join(padded_cells)} |")

                    output_lines.extend(aligned_table)
                    tables_formatted += 1
                else:
                    output_lines.extend(table_block)
            else:
                # Standardize Table caption: "Table 1: Title" -> "**Table 1.** *Title*"
                caption_match = re.match(r"^(Table\s+\d+)[:.]\s*(.*)$", stripped, re.IGNORECASE)
                if caption_match:
                    prefix = caption_match.group(1)
                    title = caption_match.group(2).strip()
                    output_lines.append(f"**{prefix}.** *{title}*")
                else:
                    output_lines.append(line)
                i += 1

        processed = "\n".join(output_lines)
        duration = (time.time() - start_time) * 1000.0
        is_modified = processed != original_text

        if tables_formatted > 0:
            diagnostics.append(f"Aligned and standardized {tables_formatted} academic table(s).")

        return SkillExecutionResult(
            skill_id=self.id,
            skill_name=self.name,
            version=self.version,
            modified=is_modified,
            text=processed,
            diagnostics=diagnostics,
            metadata={"tables_formatted": tables_formatted},
            execution_time_ms=round(duration, 2),
        )
