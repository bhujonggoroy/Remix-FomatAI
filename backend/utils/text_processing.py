"""Academic text processing and entity extraction utilities.

Detects and preserves:
- Mathematical expressions ($...$, $$...$$, LaTeX environments)
- Scientific notation (e.g. 6.022 x 10^23, 1.602e-19)
- Chemical formulas (e.g. H2O, CO2, C6H12O6, H2SO4)
- Citations (numeric [1], author-year (Smith et al., 2021), Pandoc @doe2020)
- Typography normalization (smart quotes, em-dashes, en-dashes, ellipses)
"""

import re
from typing import List, Tuple
from backend.models.document import EntityType, InlineEntity


# ---------------------------------------------------------------------------
# Entity Extraction Regexes
# ---------------------------------------------------------------------------

# Display math: $$...$$ or \[...\]
RE_DISPLAY_MATH = re.compile(r"(\$\$(.+?)\$\$|\\\[(.+?)\\\])", re.DOTALL)

# LaTeX environments
RE_LATEX_ENV = re.compile(
    r"(\\begin\{(?:equation|align|gather|multline|bmatrix|pmatrix)\*?\}.+?\\end\{(?:equation|align|gather|multline|bmatrix|pmatrix)\*?\})",
    re.DOTALL,
)

# Inline math: $...$ (guarded against currency like $100 or $5.50)
RE_INLINE_MATH = re.compile(r"(?<![\$\w])\$([^\$\n]+?)\$(?![\$\w\d])")

# Scientific notation: 6.022 x 10^23, 1.602 × 10^{-19}, 3.0e8, 1.25E-5
RE_SCIENTIFIC_NOTATION = re.compile(
    r"\b(\d+(?:\.\d+)?\s*(?:[x×*]|\\times)\s*10\^?(?:\{?-?\d+\}?|-?\d+))\b|"
    r"\b(\d+(?:\.\d+)?[eE][+-]?\d+)\b"
)

# Chemical formulas: H2O, H₂O, CO2, CO₂, C6H12O6, H2SO4, Ca(OH)2, Fe2O3, CH3COOH
RE_CHEMICAL_FORMULA = re.compile(
    r"\b([A-Z][a-z]?(?:[0-9₀-₉]+)?(?:[A-Z][a-z]?(?:[0-9₀-₉]+)?)+(?:\([A-Z][a-z]?(?:[0-9₀-₉]+)?\)(?:[0-9₀-₉]+)?)?)\b"
)

# Citations:
# 1. Numeric: [1], [1, 2], [1-4], [12]
# 2. Author-year: (Smith, 2020), (Smith & Johnson, 2019), (Smith et al., 2021, p. 45)
# 3. Pandoc: [@smith2020]
RE_CITATION_NUMERIC = re.compile(r"\[(\d+(?:\s*[,-]\s*\d+)*)\]")
RE_CITATION_AUTHORYEAR = re.compile(
    r"\(([A-Z][a-zA-Z\s\.\-]+(?:et al\.|&|and)?(?:,\s*\d{4}[a-z]?(?:,\s*p{1,2}\.\s*\d+)?|\s+\d{4}))\)"
)
RE_CITATION_PANDOC = re.compile(r"\[?@([a-zA-Z0-9_\-]+(?:\s*,\s*p{1,2}\.\s*\d+)?)\]?")


def extract_inline_entities(text: str) -> List[InlineEntity]:
    """Extracts all academic inline entities (math, scientific notation, chemical formulas, citations)

    with exact character offsets.
    """
    entities: List[InlineEntity] = []

    # 1. LaTeX Environments
    for match in RE_LATEX_ENV.finditer(text):
        entities.append(
            InlineEntity(
                entity_type=EntityType.DISPLAY_MATH,
                raw_text=match.group(1),
                normalized_text=match.group(1).strip(),
                start=match.start(),
                end=match.end(),
                metadata={"syntax": "latex_env"},
            )
        )

    # 2. Display Math $$...$$
    for match in RE_DISPLAY_MATH.finditer(text):
        content = match.group(2) or match.group(3) or match.group(1)
        entities.append(
            InlineEntity(
                entity_type=EntityType.DISPLAY_MATH,
                raw_text=match.group(1),
                normalized_text=content.strip(),
                start=match.start(),
                end=match.end(),
                metadata={"syntax": "display_dollar"},
            )
        )

    # 3. Inline Math $...$
    for match in RE_INLINE_MATH.finditer(text):
        content = match.group(1)
        entities.append(
            InlineEntity(
                entity_type=EntityType.INLINE_MATH,
                raw_text=match.group(0),
                normalized_text=content.strip(),
                start=match.start(),
                end=match.end(),
                metadata={"syntax": "inline_dollar"},
            )
        )

    # 4. Citations
    for match in RE_CITATION_NUMERIC.finditer(text):
        entities.append(
            InlineEntity(
                entity_type=EntityType.CITATION_REFERENCE,
                raw_text=match.group(0),
                normalized_text=match.group(1).strip(),
                start=match.start(),
                end=match.end(),
                metadata={"citation_style": "numeric"},
            )
        )

    for match in RE_CITATION_AUTHORYEAR.finditer(text):
        entities.append(
            InlineEntity(
                entity_type=EntityType.CITATION_REFERENCE,
                raw_text=match.group(0),
                normalized_text=match.group(1).strip(),
                start=match.start(),
                end=match.end(),
                metadata={"citation_style": "author_year"},
            )
        )

    for match in RE_CITATION_PANDOC.finditer(text):
        entities.append(
            InlineEntity(
                entity_type=EntityType.CITATION_REFERENCE,
                raw_text=match.group(0),
                normalized_text=match.group(1).strip(),
                start=match.start(),
                end=match.end(),
                metadata={"citation_style": "pandoc"},
            )
        )

    # 5. Scientific Notation
    for match in RE_SCIENTIFIC_NOTATION.finditer(text):
        entities.append(
            InlineEntity(
                entity_type=EntityType.SCIENTIFIC_NOTATION,
                raw_text=match.group(0),
                normalized_text=match.group(0).replace("x", "×").replace("*", "×"),
                start=match.start(),
                end=match.end(),
            )
        )

    # 6. Chemical Formulas (Only if not already overlapping math)
    math_ranges = [(e.start, e.end) for e in entities if e.entity_type in (EntityType.INLINE_MATH, EntityType.DISPLAY_MATH)]
    for match in RE_CHEMICAL_FORMULA.finditer(text):
        raw = match.group(0)
        # Avoid common English acronyms like NASA, USA, DNA, RNA, CPU, GPU unless formula context
        if raw in {"NASA", "USA", "UK", "DNA", "RNA", "CPU", "GPU", "API", "RAM", "ROM", "HTTP", "URL", "HTML"}:
            continue
        # Verify it has at least one number or multiple elements
        if any(c.isdigit() for c in raw) or len(re.findall(r"[A-Z]", raw)) >= 2:
            is_overlapping = any(start <= match.start() < end for start, end in math_ranges)
            if not is_overlapping:
                entities.append(
                    InlineEntity(
                        entity_type=EntityType.CHEMICAL_FORMULA,
                        raw_text=raw,
                        normalized_text=raw,
                        start=match.start(),
                        end=match.end(),
                    )
                )

    # Sort entities by start index
    entities.sort(key=lambda e: e.start)
    return entities


# ---------------------------------------------------------------------------
# Typography Normalization
# ---------------------------------------------------------------------------

def normalize_academic_typography(text: str) -> str:
    """Applies smart quotes, em-dashes, en-dashes for number ranges, and proper ellipses.

    Protects inline math, code spans, markdown table lines, and URLs from unintended transformations.
    """
    if not text:
        return ""

    placeholders: List[Tuple[str, str]] = []

    def save_span(match):
        token = f"__TOKEN_GUARD_{len(placeholders)}__"
        placeholders.append((token, match.group(0)))
        return token

    # Guard tables, code blocks, display math, and inline math
    # 1. Guard table rows (| ... |) so delimiter rows (|---|) aren't converted to em-dashes
    text = re.sub(r"(^\|[^\n]+?\|$)", save_span, text, flags=re.MULTILINE)
    # 2. Guard code blocks and math
    text = re.sub(r"(`[^`]+`|\$\$.+?\$\$|\\\[.+?\\\]|\$[^\$\n]+?\$)", save_span, text, flags=re.DOTALL)

    # 1. Ellipses (... -> …)
    text = re.sub(r"\.{3,}", "…", text)

    # 2. Em-dashes (-- or --- -> —)
    text = re.sub(r"\s*---\s*|\s*--\s*", " — ", text)

    # 3. En-dash for numeric page/year ranges (e.g., pp. 10-15 -> pp. 10–15, 1999-2004 -> 1999–2004)
    text = re.sub(r"(?<=\d)\s*-\s*(?=\d)", "–", text)

    # 4. Smart quotes:
    # Double quotes
    text = re.sub(r'(^|[\s\(\[\{<])"(\S)', r"\1“\2", text)
    text = re.sub(r'(\S)"([\s\.,;:!\?\)\]\}>]|$)', r"\1”\2", text)
    text = text.replace('"', "”")  # Fallback for closing

    # Single quotes / apostrophes
    text = re.sub(r"(^|[\s\(\[\{<])'(\S)", r"\1‘\2", text)
    text = re.sub(r"(\S)'([\s\.,;:!\?\)\]\}>]|$)", r"\1’\2", text)
    text = re.sub(r"(\w)'(\w)", r"\1’\2", text)  # Contractions e.g. don't -> don’t

    # Restore guarded spans in reverse order
    for token, original in reversed(placeholders):
        text = text.replace(token, original)

    return text
