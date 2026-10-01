"""Mathematics Detection and Normalization Utilities.

Performs robust identification of mathematical expressions in raw academic prose:
- Display math environments ($$, \\[, \\begin{equation}, etc.)
- Inline math delimiters ($, \\() with currency and punctuation protection
- Undelimited naked LaTeX constructs (\\frac, \\sqrt, \\sum, \\int, \\lim, etc.)
- Subscripted and superscripted variables (x_i, x^2, \\sigma^2)
- Matrix environments (\\begin{pmatrix}, etc.)
- Strict protection for ordinary text with slashes (e.g. "5/10 students" is NOT a fraction)
"""

import re
from typing import List, Tuple
from backend.models.math import MathSpan, MathType, TextSegment


# Standard Greek symbols (both lower and upper case)
GREEK_LETTERS = (
    r"alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|vartheta|iota|kappa|"
    r"lambda|mu|nu|xi|pi|varpi|rho|varrho|sigma|varsigma|tau|upsilon|phi|varphi|"
    r"chi|psi|omega|Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Upsilon|Phi|Psi|Omega"
)

# Currency pattern to avoid false-positive inline math
CURRENCY_PATTERN = re.compile(
    r"^\$\d+(?:,\d{3})*(?:\.\d+)?(?:\s+(?:million|billion|trillion|USD|EUR|GBP|dollars?))?$",
    re.IGNORECASE,
)

# Ordinary slash expressions that must NOT be converted to fractions
PROSE_SLASH_PATTERNS = [
    re.compile(r"\bhttps?://\S+", re.IGNORECASE),
    re.compile(r"\b\d{1,4}/\d{1,2}/\d{1,4}\b"),  # Dates
    re.compile(r"\b\d+\s*/\s*\d+\s+[a-zA-Z]+"),   # e.g., "5/10 students", "3/4 of participants"
    re.compile(r"\b(?:and/or|w/o|w/|n/a|24/7|c/o)\b", re.IGNORECASE),
]


def normalize_delimiters(text: str) -> str:
    """Normalizes alternative LaTeX math delimiters to canonical forms.

    \\[ ... \\] -> $$ ... $$
    \\begin{equation} ... \\end{equation} -> $$ ... $$
    \\begin{equation*} ... \\end{equation*} -> $$ ... $$
    \\begin{align} ... \\end{align} -> $$ \\begin{aligned} ... \\end{aligned} $$
    \\( ... \\) -> $ ... $
    """
    if not text:
        return ""

    # Replace display equations with trimmed inner content
    text = re.sub(r"\\\[\s*(.*?)\s*\\\]", r"$$\1$$", text, flags=re.DOTALL)
    text = re.sub(
        r"\\begin\{equation\*?\}\s*(.*?)\s*\\end\{equation\*?\}",
        r"$$\1$$",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"\\begin\{align\*?\}\s*(.*?)\s*\\end\{align\*?\}",
        r"$$\\begin{aligned}\1\\end{aligned}$$",
        text,
        flags=re.DOTALL,
    )
    # Replace inline equations with trimmed inner content
    text = re.sub(r"\\\(\s*(.*?)\s*\\\)", r"$\1$", text, flags=re.DOTALL)

    return text


def clean_latex(latex: str) -> str:
    """Cleans and canonicalizes a raw LaTeX mathematical expression string."""
    if not latex:
        return ""

    s = latex.strip()

    # Strip outer delimiters if present
    if s.startswith("$$") and s.endswith("$$") and len(s) >= 4:
        s = s[2:-2].strip()
    elif s.startswith("\\[") and s.endswith("\\]") and len(s) >= 4:
        s = s[2:-2].strip()
    elif s.startswith("$") and s.endswith("$") and len(s) >= 2:
        s = s[1:-1].strip()
    elif s.startswith("\\(") and s.endswith("\\)") and len(s) >= 4:
        s = s[2:-2].strip()

    # LLM cleanup: normalize escaped ampersands inside matrix if any
    s = s.replace(r"\&", "&")

    # Trim leading/trailing whitespace
    return s.strip()


def is_currency_string(token: str) -> bool:
    """Determines whether a token starting with '$' is currency rather than math."""
    cleaned = token.strip()
    if CURRENCY_PATTERN.match(cleaned):
        return True
    if re.match(r"^\$\d+(?:,\d{3})*(?:\.\d+)?(?:\s+[a-zA-Z]+)?", cleaned):
        return True
    return False


def is_prose_slash(text: str, start: int, end: int) -> bool:
    """Checks if a matched slash region is actually an ordinary prose slash (e.g. '5/10 students')."""
    window_start = max(0, start - 15)
    window_end = min(len(text), end + 25)
    window = text[window_start:window_end]

    for pat in PROSE_SLASH_PATTERNS:
        if pat.search(window):
            return True
    return False


def detect_math_spans(text: str) -> List[MathSpan]:
    """Scans raw text and extracts all mathematical expressions with character offsets.

    Sorted in non-overlapping order.
    """
    if not text:
        return []

    spans: List[MathSpan] = []
    occupied: List[Tuple[int, int]] = []

    def is_free(start: int, end: int) -> bool:
        for occ_s, occ_e in occupied:
            if not (end <= occ_s or start >= occ_e):
                return False
        return True

    def add_span(s: int, e: int, raw: str, latex: str, mtype: MathType, conf: float = 1.0):
        if is_free(s, e):
            spans.append(
                MathSpan(
                    start=s,
                    end=e,
                    raw_text=raw,
                    latex=clean_latex(latex),
                    math_type=mtype,
                    confidence=conf,
                )
            )
            occupied.append((s, e))

    # 1. Display Math: $$ ... $$
    for m in re.finditer(r"\$\$(.+?)\$\$", text, flags=re.DOTALL):
        add_span(m.start(), m.end(), m.group(0), m.group(1), MathType.DISPLAY, 1.0)

    # 2. Display Math: \[ ... \]
    for m in re.finditer(r"\\\[(.+?)\\\]", text, flags=re.DOTALL):
        add_span(m.start(), m.end(), m.group(0), m.group(1), MathType.DISPLAY, 1.0)

    # 3. Environments: \begin{equation} ... \end{equation}
    for m in re.finditer(r"\\begin\{equation\*?\}(.+?)\\end\{equation\*?\}", text, flags=re.DOTALL):
        add_span(m.start(), m.end(), m.group(0), m.group(1), MathType.DISPLAY, 1.0)

    # 4. Environments: \begin{align} ... \end{align}
    for m in re.finditer(r"\\begin\{align\*?\}(.+?)\\end\{align\*?\}", text, flags=re.DOTALL):
        aligned_content = f"\\begin{{aligned}}{m.group(1)}\\end{{aligned}}"
        add_span(m.start(), m.end(), m.group(0), aligned_content, MathType.DISPLAY, 1.0)

    # 5. Inline Math: \( ... \)
    for m in re.finditer(r"\\\((.+?)\\\)", text, flags=re.DOTALL):
        add_span(m.start(), m.end(), m.group(0), m.group(1), MathType.INLINE, 1.0)

    # 6. Inline Math: $ ... $ (with strict currency and prose checks)
    for m in re.finditer(r"(?<!\\)\$(?!\s)([^$\n]+?)(?<!\s)(?<!\\)\$", text):
        inner = m.group(1).strip()
        # Prevent false-positives for currency like "$100 million for research, but $x$"
        if re.match(r"^\d+(?:,\d{3})*(?:\.\d+)?\s+[a-zA-Z]", inner):
            continue
        if is_currency_string(m.group(0)) or inner.count("\n") > 0:
            continue
        add_span(m.start(), m.end(), m.group(0), inner, MathType.INLINE, 0.95)

    # 7. Undelimited Naked LaTeX constructs:
    # 7a. Fractions: \frac{num}{den}
    for m in re.finditer(r"\\frac\{[^{}]+?\}\{[^{}]+?\}", text):
        add_span(m.start(), m.end(), m.group(0), m.group(0), MathType.INLINE, 1.0)

    # 7b. Radicals: \sqrt{...} or \sqrt[n]{...}
    for m in re.finditer(r"\\sqrt(?:\[[^\]]+?\])?\{[^{}]+?\}", text):
        add_span(m.start(), m.end(), m.group(0), m.group(0), MathType.INLINE, 1.0)

    # 7c. Summations: \sum_{...}^{...} or \sum_{...} or \sum
    for m in re.finditer(r"\\sum(?:_\{[^{}]+?\})?(?:\^\{[^{}]+?\})?(?:\s+[a-zA-Z0-9_\^]+)?", text):
        add_span(m.start(), m.end(), m.group(0), m.group(0), MathType.INLINE, 0.95)

    # 7d. Integrals: \int_{...}^{...} or \int
    for m in re.finditer(r"\\int(?:_\{[^{}]+?\})?(?:\^\{[^{}]+?\})?(?:\s+[a-zA-Z0-9_\^\\\s]+?d[a-zA-Z])?", text):
        add_span(m.start(), m.end(), m.group(0), m.group(0), MathType.INLINE, 0.95)

    # 7e. Limits: \lim_{x \to \infty} ...
    for m in re.finditer(r"\\lim_\{[^{}]+?\}(?:\s+[^\s,;.]+)?", text):
        add_span(m.start(), m.end(), m.group(0), m.group(0), MathType.INLINE, 0.95)

    # 7f. Greek symbols with super/subscript: \sigma^2, \alpha_i, \lambda_{max}
    for m in re.finditer(rf"\\(?:{GREEK_LETTERS})(?:_\{{[^{{}}]+?\}}|_[0-9a-zA-Z]+)?(?:\^\{{[^{{}}]+?\}}|\^[0-9a-zA-Z]+)?", text):
        add_span(m.start(), m.end(), m.group(0), m.group(0), MathType.INLINE, 0.95)

    # 7g. Subscripted/superscripted single-letter academic variables: x_i, x^2, a_{ij}, \beta_1^2
    for m in re.finditer(r"\b[a-zA-Z](?:_\{[^{}]+?\}|_[0-9a-zA-Z]+)(?:\^\{[^{}]+?\}|\^[0-9a-zA-Z]+)?\b", text):
        add_span(m.start(), m.end(), m.group(0), m.group(0), MathType.INLINE, 0.9)
    for m in re.finditer(r"\b[a-zA-Z](?:\^\{[^{}]+?\}|\^[0-9a-zA-Z]+)\b", text):
        add_span(m.start(), m.end(), m.group(0), m.group(0), MathType.INLINE, 0.9)

    # 7h. Matrix environments: \begin{pmatrix} ... \end{pmatrix}
    for m in re.finditer(r"\\begin\{(?:matrix|pmatrix|bmatrix|vmatrix|Vmatrix)\}.+?\\end\{(?:matrix|pmatrix|bmatrix|vmatrix|Vmatrix)\}", text, flags=re.DOTALL):
        add_span(m.start(), m.end(), m.group(0), m.group(0), MathType.DISPLAY, 1.0)

    # Sort spans in order of start index
    spans.sort(key=lambda s: s.start)
    return spans


def segment_text(text: str) -> List[TextSegment]:
    """Splits a string of prose into a sequential series of plain text and math segments."""
    if not text:
        return []

    spans = detect_math_spans(text)
    if not spans:
        return [TextSegment(text=text, is_math=False)]

    segments: List[TextSegment] = []
    curr_pos = 0

    for span in spans:
        # Preceding plain text
        if span.start > curr_pos:
            plain_part = text[curr_pos:span.start]
            segments.append(TextSegment(text=plain_part, is_math=False))

        # Math segment
        segments.append(
            TextSegment(
                text=span.raw_text,
                is_math=True,
                math_type=span.math_type,
                latex=span.latex,
            )
        )
        curr_pos = span.end

    # Trailing plain text
    if curr_pos < len(text):
        segments.append(TextSegment(text=text[curr_pos:], is_math=False))

    return segments
