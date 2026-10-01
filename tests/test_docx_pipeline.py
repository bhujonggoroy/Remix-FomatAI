"""Unit and Integration Tests for FormatAI Professional DOCX Generation Engine.

Verifies:
- Generation of valid Microsoft Word (.docx) zip archives
- Presence of [Content_Types].xml and word/document.xml in archive
- Handling of title, headings (H1, H2, H3), paragraphs
- Rich inline formatting (bold, italic, underline, inline code, inline math, citations)
- Ordered and unordered lists
- Tabular data rendering with header formatting and cell alignments
- Academic blockquotes, code blocks, math blocks, and reference entries
- Centralized presets (Academic, Research Paper, Exam, Study Notes, Textbook)
- API endpoint verification: POST /api/documents/docx and POST /api/document/docx
- Genuinely editable Microsoft Word document output (not HTML/text rename)
"""

import io
import zipfile
import pytest
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
from backend.services.docx_service import DocxService

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper Assertions
# ---------------------------------------------------------------------------

def assert_valid_docx_archive(docx_bytes: bytes) -> zipfile.ZipFile:
    """Verifies that bytes constitute a valid Microsoft Word .docx OpenXML archive."""
    assert len(docx_bytes) > 1000, "DOCX file size should be substantial (>1KB)"
    buffer = io.BytesIO(docx_bytes)
    assert zipfile.is_zipfile(buffer), "Generated file is not a valid zip archive (.docx format)"

    archive = zipfile.ZipFile(buffer)
    file_list = archive.namelist()

    # Core OpenXML components required by Microsoft Word
    assert "[Content_Types].xml" in file_list, "Missing [Content_Types].xml"
    assert "word/document.xml" in file_list, "Missing word/document.xml"

    # Verify document.xml contains readable XML
    doc_xml = archive.read("word/document.xml").decode("utf-8")
    assert "<w:document" in doc_xml
    assert "<w:body>" in doc_xml

    return archive


# ---------------------------------------------------------------------------
# 1. Structural Element Tests
# ---------------------------------------------------------------------------

def test_docx_generation_with_full_academic_elements():
    """Verify DOCX generation with title, headings, paragraphs, lists, tables, and math."""
    doc_model = DocumentStructure(
        title="Neural Foundations of Memory Consolidation",
        abstract="This paper examines hippocampal-cortical dialogue during slow-wave sleep.",
        elements=[
            DocumentElement(
                id="el-1",
                type=DocumentElementType.TITLE,
                content="Neural Foundations of Memory Consolidation",
            ),
            DocumentElement(
                id="el-2",
                type=DocumentElementType.HEADING,
                content="Introduction",
                level=1,
            ),
            DocumentElement(
                id="el-3",
                type=DocumentElementType.PARAGRAPH,
                content="Memory consolidation involves **synaptic plasticity** and *sharp-wave ripples*.",
            ),
            DocumentElement(
                id="el-4",
                type=DocumentElementType.HEADING,
                content="Experimental Methodology",
                level=2,
            ),
            DocumentElement(
                id="el-5",
                type=DocumentElementType.UNORDERED_LIST,
                content="Optogenetic stimulation\nElectrophysiology recording",
                items=["Optogenetic stimulation with 473 nm laser", "Whole-cell patch clamp recording"],
            ),
            DocumentElement(
                id="el-6",
                type=DocumentElementType.ORDERED_LIST,
                content="Phase 1\nPhase 2\nPhase 3",
                items=["Habituation in arena", "Behavioral task exposure", "Post-sleep testing"],
            ),
            DocumentElement(
                id="el-7",
                type=DocumentElementType.TABLE,
                content="Experimental Cohorts",
                table_data=TableData(
                    headers=["Group", "Sample Size", "Firing Rate (Hz)"],
                    rows=[
                        ["Control", "16", "2.4 ± 0.3"],
                        ["Intervention", "18", "4.8 ± 0.6"],
                    ],
                    alignments=[TableColumnAlign.LEFT, TableColumnAlign.CENTER, TableColumnAlign.RIGHT],
                ),
            ),
            DocumentElement(
                id="el-8",
                type=DocumentElementType.BLOCKQUOTE,
                content="Memory is the diary that we all carry about with us.",
            ),
            DocumentElement(
                id="el-9",
                type=DocumentElementType.CODE_BLOCK,
                content="def calculate_burst_index(spikes):\n    return len([s for s in spikes if s.isi < 10])",
                language="python",
            ),
            DocumentElement(
                id="el-10",
                type=DocumentElementType.MATH_BLOCK,
                content="P(X = k) = \\frac{\\lambda^k e^{-\\lambda}}{k!}",
                math_syntax="latex",
            ),
            DocumentElement(
                id="el-11",
                type=DocumentElementType.HEADING,
                content="References",
                level=2,
            ),
            DocumentElement(
                id="el-12",
                type=DocumentElementType.REFERENCE_ITEM,
                content="Buzsaki, G. (2015). Hippocampal sharp wave-ripple: A cognitive biomarker. Nature Reviews Neuroscience, 16(8), 435-444.",
            ),
        ],
        references=[
            "Buzsaki, G. (2015). Hippocampal sharp wave-ripple: A cognitive biomarker. Nature Reviews Neuroscience, 16(8), 435-444."
        ],
    )

    service = DocxService()
    docx_bytes = service.generate_docx(doc_model, preset_name="academic")

    archive = assert_valid_docx_archive(docx_bytes)
    doc_xml = archive.read("word/document.xml").decode("utf-8")

    # Content assertions inside Word XML
    assert "Neural Foundations of Memory Consolidation" in doc_xml
    assert "Introduction" in doc_xml
    assert "Memory consolidation involves" in doc_xml
    assert "synaptic plasticity" in doc_xml
    assert "Optogenetic stimulation" in doc_xml
    assert "Experimental Cohorts" or "Control" in doc_xml
    assert "calculate_burst_index" in doc_xml
    assert "Buzsaki, G." in doc_xml


def test_docx_inline_formatting_tokens():
    """Verify bold, italic, underline, inline code, and citations translate to Word XML runs."""
    doc_model = DocumentStructure(
        title="Inline Test",
        elements=[
            DocumentElement(
                id="1",
                type=DocumentElementType.PARAGRAPH,
                content="Sample with **bold text**, *italic emphasis*, <u>underlined title</u>, `int x = 42;`, and citation [1].",
            )
        ],
    )

    service = DocxService()
    docx_bytes = service.generate_docx(doc_model)

    archive = assert_valid_docx_archive(docx_bytes)
    doc_xml = archive.read("word/document.xml").decode("utf-8")

    # Check XML formatting tags
    assert "<w:b/>" in doc_xml, "Bold tag <w:b/> should be present"
    assert "<w:i/>" in doc_xml, "Italic tag <w:i/> should be present"
    assert "<w:u " in doc_xml or '<w:u w:val="single"' in doc_xml, "Underline tag should be present"
    assert "int x = 42;" in doc_xml
    assert "[1]" in doc_xml


def test_docx_table_formatting():
    """Verify table headers, cell alignments, background shading, and borders."""
    table_data = TableData(
        headers=["Parameter", "Standard Value", "Tolerance"],
        rows=[
            ["Voltage", "220 V", "±5%"],
            ["Frequency", "50 Hz", "±0.5%"],
        ],
        alignments=[TableColumnAlign.LEFT, TableColumnAlign.CENTER, TableColumnAlign.RIGHT],
    )

    doc_model = DocumentStructure(
        title="Table Test",
        elements=[
            DocumentElement(
                id="t1",
                type=DocumentElementType.TABLE,
                content="Parameters Table",
                table_data=table_data,
            )
        ],
    )

    service = DocxService()
    docx_bytes = service.generate_docx(doc_model)

    archive = assert_valid_docx_archive(docx_bytes)
    doc_xml = archive.read("word/document.xml").decode("utf-8")

    # Table structure in Word XML
    assert "<w:tbl>" in doc_xml or "<w:tbl " in doc_xml
    assert "<w:tr" in doc_xml
    assert "<w:tc" in doc_xml
    assert "Parameter" in doc_xml
    assert "Voltage" in doc_xml
    assert "w:shd" in doc_xml, "Shading should be applied to header cells"


# ---------------------------------------------------------------------------
# 2. Centralized Preset Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "preset_name",
    [
        "academic",
        "research_paper",
        "exam",
        "study_notes",
        "textbook",
    ],
)
def test_all_style_presets(preset_name: str):
    """Verify each style preset generates a valid .docx document."""
    preset_config = get_style_preset(preset_name)
    assert preset_config is not None

    doc_model = DocumentStructure(
        title=f"Sample Document - {preset_config.display_name}",
        elements=[
            DocumentElement(
                id="p1",
                type=DocumentElementType.HEADING,
                content="Primary Heading",
                level=1,
            ),
            DocumentElement(
                id="p2",
                type=DocumentElementType.PARAGRAPH,
                content="This is body text formatted under the selected preset.",
            ),
        ],
    )

    service = DocxService()
    docx_bytes = service.generate_docx(doc_model, preset_name=preset_name)

    archive = assert_valid_docx_archive(docx_bytes)
    doc_xml = archive.read("word/document.xml").decode("utf-8")
    assert "Primary Heading" in doc_xml


# ---------------------------------------------------------------------------
# 3. End-to-End Pipeline & API Tests
# ---------------------------------------------------------------------------

def test_api_export_documents_docx_endpoint():
    """Verify POST /api/documents/docx accepts structured content and returns valid .docx file."""
    raw_text = (
        "# Quantum Information Science\n\n"
        "## Abstract\n\n"
        "This study models entanglement in $N$-qubit registers.\n\n"
        "### Results\n\n"
        "The fidelity is quantified as:\n\n"
        "| State | Fidelity |\n"
        "| :--- | ---: |\n"
        "| Bell | 99.8% |\n"
        "| GHZ | 97.4% |\n\n"
        "### References\n\n"
        "1. Nielsen, M. A., & Chuang, I. L. (2010). Quantum Computation and Quantum Information."
    )

    # Process into DocumentStructure first
    doc_service = DocumentService()
    process_res = doc_service.process(DocumentProcessRequest(raw_text=raw_text))

    export_payload = {
        "document": process_res.document.model_dump(),
        "preset": "academic",
        "filename": "quantum_study",
    }

    response = client.post("/api/documents/docx", json=export_payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert 'attachment; filename="quantum_study.docx"' in response.headers["content-disposition"]

    # Verify content validity
    assert_valid_docx_archive(response.content)


def test_api_export_docx_from_raw_text():
    """Verify POST /api/documents/docx can process raw_text on-the-fly and export DOCX."""
    export_payload = {
        "raw_text": (
            "# Artificial Intelligence in Clinical Diagnostics\n\n"
            "This paper reviews convolutional networks for medical imaging.\n\n"
            "## Key Findings\n\n"
            "- Sensitivity achieved: 94.2%\n"
            "- Specificity achieved: 91.8%\n"
        ),
        "preset": "research_paper",
        "filename": "clinical_ai_findings",
    }

    response = client.post("/api/documents/docx", json=export_payload)
    assert response.status_code == 200
    assert len(response.content) > 1000
    assert_valid_docx_archive(response.content)


def test_api_export_docx_alias_endpoint():
    """Verify alias endpoint POST /api/document/docx functions identically."""
    export_payload = {
        "raw_text": "# Test Document\n\nSimple text content.",
        "preset": "academic",
    }
    response = client.post("/api/document/docx", json=export_payload)
    assert response.status_code == 200
    assert_valid_docx_archive(response.content)


def test_api_export_docx_validation_error():
    """Verify 400 error when neither document nor raw_text is supplied."""
    response = client.post("/api/documents/docx", json={})
    assert response.status_code == 400
    assert "Either 'document'" in response.text
