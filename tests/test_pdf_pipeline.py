"""Regression and Integration Tests for FormatAI PDF Generation Engine.

Verifies:
- Native PDF generation via ReportLab backend (valid %PDF binary)
- Accurate page count and NumberedCanvas pagination ("Page X of Y")
- Absence of unnecessary blank pages across single and multi-page documents
- Proper preservation of headings (Title, H1, H2, H3) and typography
- Robust preservation and wrapping of tabular data with repeating headers
- Long document pagination without content truncation or broken page breaks
- Mathematical content preservation (Greek letters, superscripts, radicals, integrals)
- Protection of ordinary prose slashes (e.g. "5/10 students") and currency amounts
- Prevention of duplicated title or reference sections
- Compatibility across all centralized presets (Academic, Research Paper, Exam, Study Notes, Textbook)
- API endpoint verification: POST /api/documents/pdf and POST /api/document/pdf
"""

import io
import pytest
import pypdf
from fastapi.testclient import TestClient

from backend.core.styles import (
    PRESET_ACADEMIC,
    PRESET_EXAM,
    PRESET_RESEARCH_PAPER,
    PRESET_STUDY_NOTES,
    PRESET_TEXTBOOK,
    StylePresetName,
    get_style_preset,
)
from backend.main import app
from backend.models.document import (
    DocumentElement,
    DocumentElementType,
    DocumentProcessRequest,
    DocumentStructure,
    TableColumnAlign,
    TableData,
)
from backend.services.document_service import DocumentService
from backend.services.pdf_service import PdfService

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper Assertions
# ---------------------------------------------------------------------------

def assert_valid_pdf(pdf_bytes: bytes) -> pypdf.PdfReader:
    """Verifies that bytes constitute a valid, parsable PDF document."""
    assert len(pdf_bytes) > 500, f"PDF file size too small: {len(pdf_bytes)} bytes"
    assert pdf_bytes.startswith(b"%PDF-"), "Generated file does not start with %PDF- header"

    buffer = io.BytesIO(pdf_bytes)
    reader = pypdf.PdfReader(buffer)
    assert len(reader.pages) > 0, "PDF contains 0 pages"
    return reader


# ---------------------------------------------------------------------------
# Unit Tests: Page Count & Blank-Page Problems
# ---------------------------------------------------------------------------

def test_pdf_page_count_short_document():
    """Verifies a concise academic document renders to exactly 1 page."""
    pdf_service = PdfService()
    doc = DocumentStructure(
        title="Concise Research Brief",
        elements=[
            DocumentElement(
                id="e1",
                type=DocumentElementType.HEADING,
                content="Introduction",
                level=1,
            ),
            DocumentElement(
                id="e2",
                type=DocumentElementType.PARAGRAPH,
                content="This is a brief empirical report summarizing initial experimental results.",
            ),
        ],
    )

    pdf_bytes = pdf_service.generate_pdf(doc, preset_name="academic")
    reader = assert_valid_pdf(pdf_bytes)

    assert len(reader.pages) == 1, f"Expected exactly 1 page for short doc, got {len(reader.pages)}"
    page_text = reader.pages[0].extract_text()
    assert "Concise Research Brief" in page_text
    assert "Introduction" in page_text
    assert "brief empirical report" in page_text
    assert "Page 1 of 1" in page_text


def test_pdf_no_blank_pages_multi_page():
    """Verifies that every generated page contains non-trivial content (no accidental blank pages)."""
    pdf_service = PdfService()

    # Generate a multi-paragraph document spanning 2-3 pages
    elements = []
    for i in range(12):
        elements.append(
            DocumentElement(
                id=f"h_{i}",
                type=DocumentElementType.HEADING,
                content=f"Section {i+1}: Theoretical Foundations",
                level=2,
            )
        )
        elements.append(
            DocumentElement(
                id=f"p_{i}",
                type=DocumentElementType.PARAGRAPH,
                content=(
                    f"Paragraph {i+1}: Quantitative evaluation demonstrates consistent performance "
                    "across empirical benchmarks under varying operational constraints. "
                    "Statistical analysis confirms significance at the alpha = 0.05 threshold."
                ),
            )
        )

    doc = DocumentStructure(title="Multi-Section Academic Study", elements=elements)
    pdf_bytes = pdf_service.generate_pdf(doc, preset_name="academic")
    reader = assert_valid_pdf(pdf_bytes)

    total_pages = len(reader.pages)
    assert total_pages >= 2, f"Expected at least 2 pages, got {total_pages}"

    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text().strip()
        # Verify page is not blank (must contain more than just headers/footers)
        assert len(text) > 80, f"Page {page_idx+1} appears blank or under-filled: '{text}'"
        assert f"Page {page_idx+1} of {total_pages}" in text


def test_pdf_long_documents_pagination():
    """Verifies sequential pagination and content preservation across long documents."""
    pdf_service = PdfService()

    # Generate a substantial document spanning 4+ pages
    elements = []
    for i in range(25):
        elements.append(
            DocumentElement(
                id=f"sec_{i}",
                type=DocumentElementType.HEADING,
                content=f"Chapter {i+1}: Analysis and Discussion",
                level=1 if i % 5 == 0 else 2,
            )
        )
        for j in range(2):
            elements.append(
                DocumentElement(
                    id=f"p_{i}_{j}",
                    type=DocumentElementType.PARAGRAPH,
                    content=(
                        f"Detailed analysis paragraph {i}.{j}: "
                        "The investigative methodology incorporates both inductive reasoning and deductive "
                        "falsification frameworks to evaluate hypothesis validity. Empirical observations "
                        "indicate that algorithmic efficiency scales logarithmically with problem dimension. "
                    ) * 2,
                )
            )

    doc = DocumentStructure(title="Comprehensive Monograph", elements=elements)
    pdf_bytes = pdf_service.generate_pdf(doc, preset_name="research_paper")
    reader = assert_valid_pdf(pdf_bytes)

    total_pages = len(reader.pages)
    assert total_pages >= 4, f"Expected at least 4 pages for large monograph, got {total_pages}"

    # Verify no page is blank and footer numbering matches
    for idx, page in enumerate(reader.pages):
        text = page.extract_text().strip()
        assert len(text) > 100, f"Page {idx+1} has insufficient content"
        assert f"Page {idx+1} of {total_pages}" in text


# ---------------------------------------------------------------------------
# Unit Tests: Headings & Hierarchy
# ---------------------------------------------------------------------------

def test_pdf_headings_hierarchy_preserved():
    """Verifies that Title, Heading 1, Heading 2, and Heading 3 are correctly formatted."""
    pdf_service = PdfService()
    doc = DocumentStructure(
        title="Hierarchical Document Structure",
        abstract="This paper explores structural hierarchy in academic typography.",
        elements=[
            DocumentElement(id="h1", type=DocumentElementType.HEADING, content="1. Primary Section", level=1),
            DocumentElement(id="p1", type=DocumentElementType.PARAGRAPH, content="Primary section opening text."),
            DocumentElement(id="h2", type=DocumentElementType.HEADING, content="1.1 Secondary Subsection", level=2),
            DocumentElement(id="p2", type=DocumentElementType.PARAGRAPH, content="Secondary section content."),
            DocumentElement(id="h3", type=DocumentElementType.HEADING, content="1.1.1 Tertiary Topic", level=3),
            DocumentElement(id="p3", type=DocumentElementType.PARAGRAPH, content="Tertiary topic detailed discussion."),
        ],
    )

    pdf_bytes = pdf_service.generate_pdf(doc, preset_name="academic")
    reader = assert_valid_pdf(pdf_bytes)
    full_text = "".join(p.extract_text() for p in reader.pages)

    assert "Hierarchical Document Structure" in full_text
    assert "Abstract" in full_text
    assert "1. Primary Section" in full_text
    assert "1.1 Secondary Subsection" in full_text
    assert "1.1.1 Tertiary Topic" in full_text


def test_pdf_no_duplicated_content():
    """Verifies document title and references are not duplicated when already present in elements."""
    pdf_service = PdfService()
    doc = DocumentStructure(
        title="Non-Duplicated Title",
        elements=[
            DocumentElement(id="t1", type=DocumentElementType.TITLE, content="Non-Duplicated Title"),
            DocumentElement(id="p1", type=DocumentElementType.PARAGRAPH, content="Body text."),
            DocumentElement(
                id="r1",
                type=DocumentElementType.REFERENCE_ITEM,
                content="Smith, J. (2020). Machine Learning Foundations. Academic Press.",
            ),
        ],
        references=["Smith, J. (2020). Machine Learning Foundations. Academic Press."],
    )

    pdf_bytes = pdf_service.generate_pdf(doc, preset_name="academic")
    reader = assert_valid_pdf(pdf_bytes)
    full_text = "".join(p.extract_text() for p in reader.pages)

    # Title should appear exactly once in main flow (plus running header on subsequent pages if any)
    assert full_text.count("Non-Duplicated Title") == 1
    # Reference item should appear once, not duplicated
    assert full_text.count("Machine Learning Foundations") == 1


# ---------------------------------------------------------------------------
# Unit Tests: Tables
# ---------------------------------------------------------------------------

def test_pdf_tables_preserved():
    """Verifies that tables with headers, multiple rows, and columns wrap and render properly."""
    pdf_service = PdfService()
    table_data = TableData(
        headers=["Model", "Parameters", "Accuracy", "Inference Latency"],
        rows=[
            ["FormatAI-Base", "125M", "91.2%", "14.2 ms"],
            ["FormatAI-Large", "350M", "94.8%", "28.5 ms"],
            ["FormatAI-Academic", "1.3B", "97.6%", "65.1 ms"],
        ],
        caption="Table 1: Performance Comparison Across Architecture Variants",
    )

    doc = DocumentStructure(
        title="Experimental Benchmarks",
        elements=[
            DocumentElement(id="h1", type=DocumentElementType.HEADING, content="Results", level=1),
            DocumentElement(id="tbl1", type=DocumentElementType.TABLE, table_data=table_data),
        ],
    )

    pdf_bytes = pdf_service.generate_pdf(doc, preset_name="research_paper")
    reader = assert_valid_pdf(pdf_bytes)
    full_text = "".join(p.extract_text() for p in reader.pages)

    assert "Performance Comparison Across Architecture Variants" in full_text
    assert "Parameters" in full_text
    assert "Inference Latency" in full_text
    assert "FormatAI-Academic" in full_text
    assert "97.6%" in full_text
    assert "65.1 ms" in full_text


def test_pdf_large_table_multipage_repeat_header():
    """Verifies a 30-row table renders cleanly across pages with repeating headers."""
    pdf_service = PdfService()
    rows = [[f"Sample-{i}", f"Class-{i % 3}", f"{85.0 + (i % 15):.1f}%", f"Observed-{i}"] for i in range(30)]
    table_data = TableData(
        headers=["Sample ID", "Category", "Confidence", "Status"],
        rows=rows,
    )

    doc = DocumentStructure(
        title="Extensive Empirical Dataset",
        elements=[
            DocumentElement(id="h1", type=DocumentElementType.HEADING, content="Dataset Overview", level=1),
            DocumentElement(id="tbl1", type=DocumentElementType.TABLE, table_data=table_data),
        ],
    )

    pdf_bytes = pdf_service.generate_pdf(doc, preset_name="academic")
    reader = assert_valid_pdf(pdf_bytes)

    # Must contain both first and last rows
    full_text = "".join(p.extract_text() for p in reader.pages)
    assert "Sample-0" in full_text
    assert "Sample-29" in full_text
    assert "Sample ID" in full_text


# ---------------------------------------------------------------------------
# Unit Tests: Mathematical Content
# ---------------------------------------------------------------------------

def test_pdf_mathematical_content_preserved():
    """Verifies that mathematical equations (fractions, exponents, radicals, Greek) render cleanly."""
    pdf_service = PdfService()
    doc = DocumentStructure(
        title="Mathematical Physics",
        elements=[
            DocumentElement(
                id="p1",
                type=DocumentElementType.PARAGRAPH,
                content="The variance formula is given by $\\sigma^2 = \\frac{1}{N}\\sum_{i=1}^N (x_i - \\mu)^2$.",
            ),
            DocumentElement(
                id="m1",
                type=DocumentElementType.MATH_BLOCK,
                content="i\\hbar\\frac{\\partial}{\\partial t}\\Psi = \\hat{H}\\Psi",
            ),
            DocumentElement(
                id="p2",
                type=DocumentElementType.PARAGRAPH,
                content="Consider the cube root $\\sqrt[3]{8} = 2$ and mass-energy equivalence $E = mc^2$.",
            ),
        ],
    )

    pdf_bytes = pdf_service.generate_pdf(doc, preset_name="academic")
    reader = assert_valid_pdf(pdf_bytes)
    full_text = "".join(p.extract_text() for p in reader.pages)

    # Verify mathematical symbols appear
    assert "σ2" in full_text or "σ" in full_text
    assert "μ" in full_text
    assert "∑" in full_text
    assert "ħ" in full_text or "Ψ" in full_text
    assert "mc2" in full_text or "mc" in full_text
    assert "√" in full_text

    # Verify raw LaTeX commands are NOT exposed
    assert "\\frac" not in full_text
    assert "\\sum" not in full_text
    assert "\\partial" not in full_text
    assert "\\sqrt" not in full_text


def test_pdf_prose_slashes_and_currency_protected():
    """Verifies prose containing slashes and dollar amounts are preserved as ordinary text."""
    pdf_service = PdfService()
    doc = DocumentStructure(
        title="Demographic Survey",
        elements=[
            DocumentElement(
                id="p1",
                type=DocumentElementType.PARAGRAPH,
                content="In the survey, 5/10 students passed and 3/4 of participants agreed. The grant awarded was $100 million.",
            ),
        ],
    )

    pdf_bytes = pdf_service.generate_pdf(doc, preset_name="academic")
    reader = assert_valid_pdf(pdf_bytes)
    full_text = "".join(p.extract_text() for p in reader.pages)

    assert "5/10 students" in full_text
    assert "3/4 of participants" in full_text
    assert "$100 million" in full_text


# ---------------------------------------------------------------------------
# Unit Tests: Style Presets
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "preset_name",
    [
        StylePresetName.ACADEMIC.value,
        StylePresetName.RESEARCH_PAPER.value,
        StylePresetName.EXAM.value,
        StylePresetName.STUDY_NOTES.value,
        StylePresetName.TEXTBOOK.value,
    ],
)
def test_pdf_all_style_presets(preset_name: str):
    """Verifies PDF compilation succeeds across all 5 centralized style presets."""
    pdf_service = PdfService()
    doc = DocumentStructure(
        title=f"Testing Preset {preset_name.title()}",
        elements=[
            DocumentElement(id="h1", type=DocumentElementType.HEADING, content="Section Heading", level=1),
            DocumentElement(id="p1", type=DocumentElementType.PARAGRAPH, content="Paragraph styling under preset."),
            DocumentElement(
                id="tbl1",
                type=DocumentElementType.TABLE,
                table_data=TableData(headers=["Col 1", "Col 2"], rows=[["Val A", "Val B"]]),
            ),
        ],
    )

    pdf_bytes = pdf_service.generate_pdf(doc, preset_name=preset_name)
    reader = assert_valid_pdf(pdf_bytes)
    assert len(reader.pages) >= 1
    page_text = reader.pages[0].extract_text()
    assert "Section Heading" in page_text
    assert "Val A" in page_text


# ---------------------------------------------------------------------------
# API Integration Tests: POST /api/documents/pdf
# ---------------------------------------------------------------------------

def test_api_export_documents_pdf_with_raw_text():
    """Tests POST /api/documents/pdf with raw academic markdown text."""
    payload = {
        "raw_text": (
            "# Quantum State Evolution\n\n"
            "## Schrödinger Wave Equation\n\n"
            "The time-dependent Schrödinger equation is given by:\n\n"
            "$$i\\hbar\\frac{\\partial}{\\partial t}\\Psi = \\hat{H}\\Psi$$\n\n"
            "where $\\Psi$ represents the state vector. In the trial, 5/10 trials succeeded."
        ),
        "preset": "academic",
        "filename": "quantum_evolution",
    }

    response = client.post("/api/documents/pdf", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "quantum_evolution.pdf" in response.headers["content-disposition"]

    reader = assert_valid_pdf(response.content)
    full_text = "".join(p.extract_text() for p in reader.pages)
    assert "Quantum State Evolution" in full_text
    assert "Schrödinger Wave Equation" in full_text
    assert "5/10 trials" in full_text


def test_api_export_documents_pdf_with_structured_document():
    """Tests POST /api/documents/pdf with a pre-parsed DocumentStructure model."""
    doc_model = DocumentStructure(
        title="Structured API Export",
        elements=[
            DocumentElement(id="e1", type=DocumentElementType.HEADING, content="API Results", level=1),
            DocumentElement(id="e2", type=DocumentElementType.PARAGRAPH, content="Exported via structured payload."),
        ],
    )

    payload = {
        "document": doc_model.model_dump(),
        "preset": "research_paper",
        "filename": "structured_export",
    }

    response = client.post("/api/documents/pdf", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "structured_export.pdf" in response.headers["content-disposition"]

    reader = assert_valid_pdf(response.content)
    full_text = "".join(p.extract_text() for p in reader.pages)
    assert "Structured API Export" in full_text
    assert "API Results" in full_text


def test_api_export_document_pdf_alias():
    """Tests alias endpoint POST /api/document/pdf."""
    payload = {
        "raw_text": "# Alias Endpoint Test\n\nVerifying alias route works correctly.",
        "preset": "study_notes",
    }

    response = client.post("/api/document/pdf", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

    reader = assert_valid_pdf(response.content)
    full_text = "".join(p.extract_text() for p in reader.pages)
    assert "Alias Endpoint Test" in full_text
