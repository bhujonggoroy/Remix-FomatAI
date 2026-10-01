"""Comprehensive Tests for FormatAI Dedicated Mathematics Processing Pipeline.

Tests:
- Inline math detection ($, \\()
- Display math detection ($$, \\[, \\begin{equation}, \\begin{align})
- Fractions (simple and nested)
- Superscripts, subscripts, and combined sub/superscripts
- Radicals and square roots
- Greek symbols (lower and upper case)
- Summations, integrals, and limits
- Matrices and systems of equations
- Mixed text + math (verifying prose slashes like '5/10 students' remain uncorrupted)
- Word OMML structure in OpenXML word/document.xml
- Complete absence of exposed raw LaTeX in exported Word paragraphs
- Known limitations and graceful fallback handling
"""

import io
import zipfile
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.document import (
    DocumentElement,
    DocumentElementType,
    DocumentStructure,
)
from backend.models.math import MathType
from backend.services.docx_service import DocxService
from backend.services.math_service import MathService
from backend.utils.math_detector import (
    clean_latex,
    detect_math_spans,
    normalize_delimiters,
    segment_text,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Delimiter Normalization & Detection Tests
# ---------------------------------------------------------------------------

def test_normalize_delimiters():
    """Verify various LaTeX delimiters normalize to canonical display/inline forms."""
    text = (
        "Inline: \\( \\alpha + \\beta \\)\n"
        "Display bracket: \\[ \\frac{x}{y} \\]\n"
        "Display equation: \\begin{equation} E = mc^2 \\end{equation}\n"
        "Display align: \\begin{align} a &= b \\\\ c &= d \\end{align}"
    )
    normalized = normalize_delimiters(text)
    assert "$\\alpha + \\beta$" in normalized
    assert "$$\\frac{x}{y}$$" in normalized
    assert "$$E = mc^2$$" in normalized
    assert "\\begin{aligned}" in normalized


def test_detect_math_spans_inline_and_display():
    """Verify detector extracts inline and display equations with offsets."""
    text = "Let $f(x) = x^2$ be a function. Its integral is:\n$$\\int_0^1 x^2 dx = \\frac{1}{3}$$"
    spans = detect_math_spans(text)
    assert len(spans) == 2

    # Inline span
    assert spans[0].math_type == MathType.INLINE
    assert spans[0].latex == "f(x) = x^2"

    # Display span
    assert spans[1].math_type == MathType.DISPLAY
    assert "\\int_0^1 x^2 dx = \\frac{1}{3}" in spans[1].latex


def test_prose_slash_protection():
    """Verify that ordinary text containing '/' (e.g. '5/10 students') is NOT treated as math."""
    prose = "In this trial, 5/10 students passed, representing 3/4 of participants. See https://doi.org/10.1000/182."
    spans = detect_math_spans(prose)
    # None of these prose slashes should be detected as math spans
    assert len(spans) == 0

    segments = segment_text(prose)
    assert len(segments) == 1
    assert not segments[0].is_math
    assert "5/10 students" in segments[0].text


def test_currency_protection():
    """Verify that currency strings like '$100 USD' are not mistaken for inline math."""
    text = "The grant awarded $100 million for research, but $x$ remained unknown."
    spans = detect_math_spans(text)
    assert len(spans) == 1
    assert spans[0].latex == "x"


def test_naked_latex_detection():
    """Verify detection of naked LaTeX constructs without explicit delimiters."""
    text = "Calculate \\frac{a}{b} and evaluate \\sqrt{25} when \\sigma^2 is known."
    spans = detect_math_spans(text)
    latex_items = [s.latex for s in spans]
    assert "\\frac{a}{b}" in latex_items
    assert "\\sqrt{25}" in latex_items
    assert "\\sigma^2" in latex_items


# ---------------------------------------------------------------------------
# 2. LaTeX to OMML Conversion Tests
# ---------------------------------------------------------------------------

def test_latex_to_omml_simple_fraction():
    """Verify simple fraction \\frac{x}{y} converts to native OMML."""
    math_svc = MathService()
    res = math_svc.latex_to_omml(r"\frac{x}{y}")
    assert res.success is True
    assert "<m:oMath" in res.omml
    assert "<m:f>" in res.omml or "<m:f " in res.omml
    assert "<m:num>" in res.omml
    assert "<m:den>" in res.omml


def test_latex_to_omml_nested_fractions():
    """Verify nested fractions compile correctly."""
    math_svc = MathService()
    res = math_svc.latex_to_omml(r"\frac{\frac{a}{b}}{\frac{c}{d}}")
    assert res.success is True
    assert res.omml.count("<m:f") >= 3  # Outer fraction and two inner fractions


def test_latex_to_omml_superscripts_and_subscripts():
    """Verify superscripts (x^2), subscripts (x_i), and combinations (\\sigma_1^2)."""
    math_svc = MathService()

    # Superscript
    res_sup = math_svc.latex_to_omml(r"x^2")
    assert res_sup.success is True
    assert "<m:sSup>" in res_sup.omml or "<m:sSup " in res_sup.omml

    # Subscript
    res_sub = math_svc.latex_to_omml(r"x_i")
    assert res_sub.success is True
    assert "<m:sSub>" in res_sub.omml or "<m:sSub " in res_sub.omml

    # Combined Sub-Superscript
    res_subsup = math_svc.latex_to_omml(r"\sigma_1^2")
    assert res_subsup.success is True
    assert "<m:sSubSup>" in res_subsup.omml or ("<m:sSub" in res_subsup.omml and "<m:sSup" in res_subsup.omml)


def test_latex_to_omml_radicals():
    """Verify square roots and nth roots."""
    math_svc = MathService()

    # Square root
    res_sqrt = math_svc.latex_to_omml(r"\sqrt{x}")
    assert res_sqrt.success is True
    assert "<m:rad>" in res_sqrt.omml or "<m:rad " in res_sqrt.omml

    # Cube root
    res_root3 = math_svc.latex_to_omml(r"\sqrt[3]{8}")
    assert res_root3.success is True
    assert "<m:rad>" in res_root3.omml


def test_latex_to_omml_greek_letters():
    """Verify lowercase and uppercase Greek letters."""
    math_svc = MathService()
    res = math_svc.latex_to_omml(r"\alpha + \beta = \Gamma")
    assert res.success is True
    assert "<m:oMath" in res.omml


def test_latex_to_omml_nary_operators():
    """Verify summations, integrals, and limits."""
    math_svc = MathService()

    # Summation
    res_sum = math_svc.latex_to_omml(r"\sum_{i=1}^{n} x_i")
    assert res_sum.success is True
    assert "<m:nary>" in res_sum.omml or "<m:nary " in res_sum.omml

    # Integral
    res_int = math_svc.latex_to_omml(r"\int_{0}^{\infty} e^{-x} dx")
    assert res_int.success is True
    assert "<m:nary>" in res_int.omml or "<m:nary " in res_int.omml

    # Limit
    res_lim = math_svc.latex_to_omml(r"\lim_{x \to 0} \frac{\sin x}{x}")
    assert res_lim.success is True
    assert "<m:oMath" in res_lim.omml


def test_latex_to_omml_matrix():
    """Verify 2x2 matrix conversion."""
    math_svc = MathService()
    res = math_svc.latex_to_omml(r"\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}", is_display=True)
    assert res.success is True
    assert "<m:m>" in res.omml or "<m:m " in res.omml
    assert "<m:mr>" in res.omml  # Matrix row


def test_latex_to_omml_accents_and_groupchr():
    """Verify that bar, vec, underline with groupChr tags produce valid well-formed OMML without XML parse errors."""
    from docx import Document
    math_svc = MathService()

    expressions = [
        r"\bar{z}",
        r"\vec{v}",
        r"\underline{x}",
        r"\sigma^2 = \frac{1}{N} \sum_{i=1}^{N} (z_i - \bar{z})^2",
    ]

    for expr in expressions:
        res = math_svc.latex_to_omml(expr)
        assert res.success is True
        assert "<m:oMath" in res.omml
        # Verify tag mismatch bug is eliminated
        assert "</m:groupChrPr>" in res.omml or "<m:groupChrPr" not in res.omml

        # Verify paragraph rendering succeeds with native OMML and does not use fallback
        doc = Document()
        p = doc.add_paragraph()
        rendered_native = math_svc.render_math_to_paragraph(p, expr)
        assert rendered_native is True, f"Native OMML parsing failed for expression: {expr}"


def test_latex_to_omml_graceful_fallback():
    """Verify that unparseable LaTeX degrades gracefully without raising unhandled exceptions."""
    math_svc = MathService()
    # Malformed LaTeX syntax with unclosed environment
    res = math_svc.latex_to_omml(r"\begin{matrix} 1 & 2")
    assert res.success is False
    assert res.unicode_fallback is not None
    assert len(res.unicode_fallback) > 0


# ---------------------------------------------------------------------------
# 3. DOCX OpenXML Synthesis & Visual Verification Tests
# ---------------------------------------------------------------------------

def test_docx_rendering_no_raw_latex_exposed():
    """CRITICAL: Verify that the generated DOCX does NOT expose raw LaTeX in text runs."""
    doc_model = DocumentStructure(
        title="Mathematics Assessment",
        elements=[
            DocumentElement(
                id="e1",
                type=DocumentElementType.PARAGRAPH,
                content="The variance is given by $\\sigma^2 = \\frac{1}{N}\\sum_{i=1}^{N}(x_i - \\mu)^2$ for $N$ observations.",
            ),
            DocumentElement(
                id="e2",
                type=DocumentElementType.PARAGRAPH,
                content="Among 5/10 students, the root was $\\sqrt{4} = 2$.",
            ),
            DocumentElement(
                id="e3",
                type=DocumentElementType.MATH_BLOCK,
                content=r"\int_0^1 \frac{x^2}{\sqrt{1-x^2}} dx",
                math_syntax="latex",
            ),
        ],
    )

    docx_svc = DocxService()
    docx_bytes = docx_svc.generate_docx(doc_model)

    # Verify valid zip
    buffer = io.BytesIO(docx_bytes)
    assert zipfile.is_zipfile(buffer)
    archive = zipfile.ZipFile(buffer)
    doc_xml = archive.read("word/document.xml").decode("utf-8")

    # 1. Native OMML elements must exist in the document
    assert "<m:oMath" in doc_xml, "Native OMML must be present in word/document.xml"
    assert "<m:f" in doc_xml, "OMML fraction tag must be present"
    assert "<m:rad" in doc_xml, "OMML radical tag must be present"
    assert "<m:nary" in doc_xml, "OMML summation/integral tag must be present"

    # 2. Raw LaTeX strings must NOT appear as plain Word text (<w:t>)
    assert "<w:t>\\frac{1}{N}</w:t>" not in doc_xml
    assert "<w:t>\\sigma^2</w:t>" not in doc_xml
    assert "<w:t>\\sqrt{4}</w:t>" not in doc_xml

    # 3. Prose slashes must be preserved cleanly in plain text
    assert "5/10 students" in doc_xml


def test_api_docx_export_with_complex_mathematics():
    """Verify full-stack /api/documents/docx endpoint generates valid DOCX with native OMML."""
    payload = {
        "raw_text": (
            "# Advanced Mathematical Analysis\n\n"
            "## Quantum Statistics\n\n"
            "The partition function is defined as:\n\n"
            "$$\\mathcal{Z} = \\sum_{n=0}^{\\infty} e^{-\\beta E_n}$$\n\n"
            "where $\\beta = \\frac{1}{k_B T}$ and $E_n = \\left(n + \\frac{1}{2}\\right)\\hbar \\omega$.\n\n"
            "Notice that 3/5 experiments confirmed the energy levels."
        ),
        "preset": "academic",
        "filename": "quantum_math_paper",
    }

    response = client.post("/api/documents/docx", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    buffer = io.BytesIO(response.content)
    assert zipfile.is_zipfile(buffer)
    archive = zipfile.ZipFile(buffer)
    doc_xml = archive.read("word/document.xml").decode("utf-8")

    # Native Word equations present
    assert "<m:oMathPara" in doc_xml or "<m:oMath" in doc_xml
    assert "<m:f" in doc_xml
    assert "3/5 experiments" in doc_xml
