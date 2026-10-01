"""Academic Document Processing & DOCX Export API Routes."""

import re
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from backend.api.deps import get_document_service, get_docx_service, get_pdf_service
from backend.models.document import (
    DocumentAnalysis,
    DocumentDocxExportRequest,
    DocumentPdfExportRequest,
    DocumentProcessRequest,
    DocumentProcessResponse,
    DocumentStructure,
)
from backend.services.document_service import DocumentService
from backend.services.docx_service import DocxService
from backend.services.pdf_service import PdfService

router = APIRouter(tags=["Document Processing & Export"])

DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME_TYPE = "application/pdf"


def _handle_docx_export(
    payload: DocumentDocxExportRequest,
    document_service: DocumentService,
    docx_service: DocxService,
) -> Response:
    """Core export handler generating valid .docx file response."""
    # 1. Resolve or compute DocumentStructure
    target_doc: DocumentStructure
    if payload.document is not None:
        target_doc = payload.document
    elif payload.raw_text:
        process_res = document_service.process(
            DocumentProcessRequest(raw_text=payload.raw_text, options=payload.options)
        )
        target_doc = process_res.document
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'document' (structured document model) or 'raw_text' must be provided.",
        )

    # 2. Generate DOCX binary bytes
    docx_bytes = docx_service.generate_docx(
        document=target_doc,
        preset_name=payload.preset,
    )

    # 3. Determine clean attachment filename
    raw_name = payload.filename or target_doc.title or "academic_document"
    clean_name = re.sub(r"[^a-zA-Z0-9_\- ]", "", raw_name).strip() or "academic_document"
    safe_filename = clean_name.replace(" ", "_")
    if not safe_filename.endswith(".docx"):
        safe_filename += ".docx"

    return Response(
        content=docx_bytes,
        media_type=DOCX_MIME_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Content-Type": DOCX_MIME_TYPE,
            "Cache-Control": "no-cache",
        },
    )


@router.post(
    "/api/document/process",
    response_model=DocumentProcessResponse,
    summary="Process Raw Academic Content",
    description="Executes the full pipeline: Raw Input → Content Analysis → Content Cleanup → Structure Detection → Formatting Rules → Document Model.",
)
def process_document(
    payload: DocumentProcessRequest,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentProcessResponse:
    """Processes raw academic text into a structured internal document model."""
    try:
        return document_service.process(payload)
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "DOCUMENT_PROCESSING_FAILED",
                    "message": str(exc),
                },
            },
        )


@router.post(
    "/api/document/analyze",
    response_model=DocumentAnalysis,
    summary="Analyze Academic Content Structure",
    description="Performs structural and quality analysis on academic content without transforming it.",
)
def analyze_document(
    payload: DocumentProcessRequest,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentAnalysis:
    """Analyzes raw academic text structure, headings, math density, and citations."""
    return document_service.analyze_content(payload.raw_text)


@router.post(
    "/api/documents/docx",
    summary="Export Structured Document to Microsoft Word (.docx)",
    description="Consumes FormatAI DocumentStructure (or raw text) and returns a genuine, editable .docx file.",
    response_class=Response,
    responses={
        200: {
            "content": {DOCX_MIME_TYPE: {}},
            "description": "Genuine, editable Microsoft Word document binary",
        }
    },
)
def export_documents_docx(
    payload: DocumentDocxExportRequest,
    document_service: DocumentService = Depends(get_document_service),
    docx_service: DocxService = Depends(get_docx_service),
) -> Response:
    """Primary DOCX export endpoint at /api/documents/docx."""
    return _handle_docx_export(payload, document_service, docx_service)


@router.post(
    "/api/document/docx",
    summary="Export Structured Document to Microsoft Word (.docx) [Alias]",
    description="Alias endpoint for /api/documents/docx.",
    response_class=Response,
)
def export_document_docx_alias(
    payload: DocumentDocxExportRequest,
    document_service: DocumentService = Depends(get_document_service),
    docx_service: DocxService = Depends(get_docx_service),
) -> Response:
    """Alias DOCX export endpoint at /api/document/docx."""
    return _handle_docx_export(payload, document_service, docx_service)


def _handle_pdf_export(
    payload: DocumentPdfExportRequest,
    document_service: DocumentService,
    pdf_service: PdfService,
) -> Response:
    """Core export handler generating valid .pdf file response."""
    # 1. Resolve or compute DocumentStructure
    target_doc: DocumentStructure
    if payload.document is not None:
        target_doc = payload.document
    elif payload.raw_text:
        process_res = document_service.process(
            DocumentProcessRequest(raw_text=payload.raw_text, options=payload.options)
        )
        target_doc = process_res.document
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'document' (structured document model) or 'raw_text' must be provided.",
        )

    # 2. Generate PDF binary bytes
    pdf_bytes = pdf_service.generate_pdf(
        document=target_doc,
        preset_name=payload.preset,
    )

    # 3. Determine clean attachment filename
    raw_name = payload.filename or target_doc.title or "academic_document"
    clean_name = re.sub(r"[^a-zA-Z0-9_\- ]", "", raw_name).strip() or "academic_document"
    safe_filename = clean_name.replace(" ", "_")
    if not safe_filename.endswith(".pdf"):
        safe_filename += ".pdf"

    return Response(
        content=pdf_bytes,
        media_type=PDF_MIME_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Content-Type": PDF_MIME_TYPE,
            "Cache-Control": "no-cache",
        },
    )


@router.post(
    "/api/documents/pdf",
    summary="Export Structured Document to Adobe PDF (.pdf)",
    description="Consumes FormatAI DocumentStructure (or raw text) and returns a publication-grade .pdf file.",
    response_class=Response,
    responses={
        200: {
            "content": {PDF_MIME_TYPE: {}},
            "description": "Publication-grade Adobe PDF document binary",
        }
    },
)
def export_documents_pdf(
    payload: DocumentPdfExportRequest,
    document_service: DocumentService = Depends(get_document_service),
    pdf_service: PdfService = Depends(get_pdf_service),
) -> Response:
    """Primary PDF export endpoint at /api/documents/pdf."""
    return _handle_pdf_export(payload, document_service, pdf_service)


@router.post(
    "/api/document/pdf",
    summary="Export Structured Document to Adobe PDF (.pdf) [Alias]",
    description="Alias endpoint for /api/documents/pdf.",
    response_class=Response,
)
def export_document_pdf_alias(
    payload: DocumentPdfExportRequest,
    document_service: DocumentService = Depends(get_document_service),
    pdf_service: PdfService = Depends(get_pdf_service),
) -> Response:
    """Alias PDF export endpoint at /api/document/pdf."""
    return _handle_pdf_export(payload, document_service, pdf_service)

