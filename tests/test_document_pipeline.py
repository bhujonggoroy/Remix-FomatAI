"""Comprehensive tests for the FormatAI Document Processing Pipeline.

Tests all major academic content types:
- Title, headings, and subheadings
- Paragraphs & fragmented paragraph consolidation
- Ordered and unordered lists
- Tables (headers, rows, alignment)
- Blockquotes and code blocks
- Mathematical expressions ($...$, $$...$$, LaTeX)
- Scientific notation & chemical formulas
- Citations & reference list items
- Content cleanup vs Formatting cleanup separation
- End-to-end API pipeline
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models.document import (
    DocumentElementType,
    DocumentProcessRequest,
    EntityType,
)
from backend.services.content_cleanup_service import ContentCleanupService
from backend.services.document_service import DocumentService
from backend.services.formatting_service import FormattingService

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Content Cleanup Tests
# ---------------------------------------------------------------------------

def test_content_cleanup_removes_ai_noise():
    """Verify AI preambles and postscripts are cleanly stripped without altering paper body."""
    raw = (
        "Certainly! Here is the academic paper on quantum physics:\n\n"
        "# Quantum Entanglement\n\n"
        "This paper explores non-local correlations in entangled photon pairs.\n\n"
        "I hope this helps! Let me know if you would like any further adjustments."
    )
    cleanup_service = ContentCleanupService()
    cleaned = cleanup_service.cleanup(raw)

    assert "Certainly" not in cleaned
    assert "quantum physics:" not in cleaned
    assert "I hope this helps" not in cleaned
    assert "# Quantum Entanglement" in cleaned
    assert "This paper explores non-local correlations" in cleaned


def test_content_cleanup_removes_redundant_headings():
    """Verify empty headings and consecutive duplicate headings are eliminated."""
    raw = (
        "# Introduction\n\n"
        "# Introduction\n\n"
        "## \n\n"
        "Academic content begins here."
    )
    cleanup_service = ContentCleanupService()
    cleaned = cleanup_service.cleanup(raw)

    assert cleaned.count("# Introduction") == 1
    assert "##" not in cleaned
    assert "Academic content begins here." in cleaned


def test_content_cleanup_converts_orphan_narrative_bullets():
    """Verify isolated orphan bullets containing long narrative sentences are converted to paragraphs."""
    raw = (
        "# Overview\n\n"
        "* This investigation examines the neural mechanisms underlying human episodic memory retention. "
        "We recruited forty-two healthy adult participants across three rigorous laboratory sessions.\n\n"
        "Further discussion follows."
    )
    cleanup_service = ContentCleanupService()
    cleaned = cleanup_service.cleanup(raw)

    # Bullet marker should be removed, converting to standard paragraph
    assert not cleaned.startswith("*")
    assert "This investigation examines the neural mechanisms" in cleaned


# ---------------------------------------------------------------------------
# 2. Formatting Cleanup Tests
# ---------------------------------------------------------------------------

def test_formatting_service_fixes_heading_hierarchy():
    """Verify disconnected heading jumps (# to ###) are fixed to contiguous levels (# to ##)."""
    raw = (
        "# Primary Title\n\n"
        "### First Subheading\n\n"
        "#### Deeper Subheading"
    )
    formatting_service = FormattingService()
    formatted, diag = formatting_service.format_document(raw)

    assert "# Primary Title" in formatted
    assert "## First Subheading" in formatted
    assert "### Deeper Subheading" in formatted
    assert any("heading hierarchy" in d.lower() for d in diag)


def test_formatting_service_normalizes_typography():
    """Verify smart quotes, em-dashes, en-dash ranges, and ellipses are applied."""
    raw = 'The "quantum leap" -- as described by researchers ... spanned pp. 45-50.'
    formatting_service = FormattingService()
    formatted, _ = formatting_service.format_document(raw, apply_typography=True)

    assert "“quantum leap”" in formatted
    assert "—" in formatted
    assert "…" in formatted
    assert "45–50" in formatted


def test_formatting_service_normalizes_lists():
    """Verify inconsistent bullets (*, +) convert to '-' and broken numbering is fixed."""
    raw = (
        "* Item Alpha\n"
        "+ Item Beta\n"
        "- Item Gamma\n\n"
        "1. First\n"
        "1. Second\n"
        "1. Third"
    )
    formatting_service = FormattingService()
    formatted, diag = formatting_service.format_document(raw)

    assert "- Item Alpha" in formatted
    assert "- Item Beta" in formatted
    assert "- Item Gamma" in formatted
    assert "1. First" in formatted
    assert "2. Second" in formatted
    assert "3. Third" in formatted


# ---------------------------------------------------------------------------
# 3. Structure Detection & Content Types Tests
# ---------------------------------------------------------------------------

def test_structure_detection_tables():
    """Verify Markdown tables are parsed into structured TableData."""
    raw = (
        "| Sample | Concentration (mM) | Yield (%) |\n"
        "| :--- | :---: | ---: |\n"
        "| A1 | 12.5 | 88.4 |\n"
        "| B2 | 25.0 | 94.1 |"
    )
    service = DocumentService()
    res = service.process(DocumentProcessRequest(raw_text=raw))
    tables = [e for e in res.document.elements if e.type == DocumentElementType.TABLE]

    assert len(tables) == 1
    table_data = tables[0].table_data
    assert table_data is not None
    assert table_data.headers == ["Sample", "Concentration (mM)", "Yield (%)"]
    assert len(table_data.rows) == 2
    assert table_data.rows[0] == ["A1", "12.5", "88.4"]


def test_structure_detection_math_and_latex():
    """Verify display math, inline math, and LaTeX formulas are identified and tagged."""
    raw = (
        "# Mathematical Foundations\n\n"
        "The energy relationship is given by $E = mc^2$, where $c$ represents light speed.\n\n"
        "$$\n"
        "\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}\n"
        "$$"
    )
    service = DocumentService()
    res = service.process(DocumentProcessRequest(raw_text=raw))

    math_blocks = [e for e in res.document.elements if e.type == DocumentElementType.MATH_BLOCK]
    assert len(math_blocks) == 1
    assert "\\int" in math_blocks[0].content

    # Check inline math entity in paragraph
    paras = [e for e in res.document.elements if e.type == DocumentElementType.PARAGRAPH]
    assert len(paras) == 1
    math_entities = [ent for ent in paras[0].entities if ent.entity_type == EntityType.INLINE_MATH]
    assert len(math_entities) >= 1
    assert any("E = mc^2" in m.normalized_text for m in math_entities)


def test_structure_detection_scientific_and_chemical():
    """Verify scientific notation and chemical formulas are extracted as entities."""
    raw = (
        "The reaction of H2O and CO2 produces C6H12O6 in photosynthetic pathways. "
        "Avogadro's constant is 6.022 x 10^23 molecules per mole."
    )
    service = DocumentService()
    res = service.process(DocumentProcessRequest(raw_text=raw))

    para = res.document.elements[0]
    entity_types = [ent.entity_type for ent in para.entities]

    assert EntityType.CHEMICAL_FORMULA in entity_types
    assert EntityType.SCIENTIFIC_NOTATION in entity_types

    chem_entities = [ent.normalized_text for ent in para.entities if ent.entity_type == EntityType.CHEMICAL_FORMULA]
    assert any(x in chem_entities for x in ["H2O", "H₂O", "CO2", "CO₂", "C6H12O6", "C₆H₁₂O₆"])


def test_structure_detection_citations_and_references():
    """Verify numeric citations, author-year citations, and references section items."""
    raw = (
        "# Literature Review\n\n"
        "Previous findings (Smith et al., 2021) demonstrated significant effects [1, 2].\n\n"
        "# References\n\n"
        "1. Smith, J., & Johnson, K. (2021). Neural Networks in Cognition. Journal of AI, 12(3), 45-60.\n"
        "2. Doe, A. (2020). Deep Learning Foundations. Academic Press."
    )
    service = DocumentService()
    res = service.process(DocumentProcessRequest(raw_text=raw))

    # Citations detected
    review_para = [e for e in res.document.elements if e.type == DocumentElementType.PARAGRAPH][0]
    citations = [ent for ent in review_para.entities if ent.entity_type == EntityType.CITATION_REFERENCE]
    assert len(citations) >= 2

    # References detected
    assert len(res.document.references) >= 2
    assert any("Smith" in r for r in res.document.references)
    assert any("Doe" in r for r in res.document.references)


def test_structure_detection_blockquotes_and_code():
    """Verify quotations and fenced code blocks are parsed into dedicated elements."""
    raw = (
        "> \"Science is not only a disciple of reason but also one of romance and passion.\"\n\n"
        "```python\n"
        "def compute_entropy(p):\n"
        "    return -sum(pi * log2(pi) for pi in p if pi > 0)\n"
        "```"
    )
    service = DocumentService()
    res = service.process(DocumentProcessRequest(raw_text=raw))

    quotes = [e for e in res.document.elements if e.type == DocumentElementType.BLOCKQUOTE]
    codes = [e for e in res.document.elements if e.type == DocumentElementType.CODE_BLOCK]

    assert len(quotes) == 1
    assert "Science is not only" in quotes[0].content

    assert len(codes) == 1
    assert codes[0].language == "python"
    assert "def compute_entropy" in codes[0].content


# ---------------------------------------------------------------------------
# 4. End-to-End API Routes Tests
# ---------------------------------------------------------------------------

def test_api_process_document_endpoint():
    """Verify POST /api/document/process executes the complete pipeline and returns structured model."""
    payload = {
        "raw_text": (
            "Certainly! Here is your formatted paper:\n\n"
            "# Deep Learning in Genomic Medicine\n\n"
            "## Abstract\n\n"
            "This study investigates convolution operations on genomic sequences.\n\n"
            "### Methodology\n\n"
            "We sequenced DNA molecules in H2O solution with concentration 1.5 x 10^3 nM.\n\n"
            "| Batch | Precision |\n"
            "| :--- | ---: |\n"
            "| 01 | 99.2% |\n\n"
            "$$ \\sigma(z) = \\frac{1}{1 + e^{-z}} $$\n\n"
            "### References\n\n"
            "1. Watson, J. (2020). Genomic Analysis Protocols."
        ),
        "options": {
            "enable_content_cleanup": True,
            "enable_formatting_cleanup": True,
            "target_style": "APA",
            "smart_typography": True,
        },
    }

    response = client.post("/api/document/process", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True

    doc = data["document"]
    assert doc["title"] == "Deep Learning in Genomic Medicine"
    assert doc["stats"]["word_count"] > 20
    assert doc["stats"]["table_count"] == 1
    assert doc["stats"]["math_block_count"] == 1
    assert len(doc["elements"]) >= 5

    analysis = data["analysis"]
    assert analysis["has_abstract"] is True
    assert analysis["has_references"] is True
    assert analysis["structure_quality_score"] > 50


def test_api_analyze_document_endpoint():
    """Verify POST /api/document/analyze reports diagnostics without transforming document."""
    payload = {
        "raw_text": "# Machine Learning Paper\n\nAbstract: A short study.\n\n$E=mc^2$\n\n[1] Reference."
    }
    response = client.post("/api/document/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["detected_title"] == "Machine Learning Paper"
    assert "detected_entities_summary" in data
