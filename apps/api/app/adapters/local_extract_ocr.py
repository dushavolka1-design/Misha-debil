from __future__ import annotations

from dar.providers.ports import OcrDocumentResult, OCRProvider, StoredObject

from app.services.analysis.document_extract import extract_document_pages


class LocalExtractOCRProvider(OCRProvider):
    """Local PyMuPDF/pypdf/docx/tesseract extraction from real uploaded bytes."""

    name = "local_extract"
    model_version = "local-extract-1"

    async def extract_text(self, *, object_ref: StoredObject, content_type: str) -> OcrDocumentResult:
        return await self.extract_layout(object_ref=object_ref, content_type=content_type)

    async def extract_layout(
        self,
        *,
        object_ref: StoredObject,
        content_type: str,
        page_bytes: bytes | None = None,
        fixture_id: str | None = None,
    ) -> OcrDocumentResult:
        _ = (object_ref, fixture_id)
        if not page_bytes:
            return OcrDocumentResult(pages=[], provider=self.name, model_version=self.model_version)
        detected = "pdf"
        if "word" in content_type or content_type.endswith("docx"):
            detected = "docx"
        elif content_type.startswith("image/"):
            detected = "jpeg"
        return extract_document_pages(page_bytes, detected_type=detected, content_type=content_type)
