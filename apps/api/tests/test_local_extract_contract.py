from __future__ import annotations

import io
import unittest

from dar.providers.ports import StoredObject
from reportlab.pdfgen.canvas import Canvas

from app.adapters.local_extract_ocr import LocalExtractOCRProvider


class LocalExtractContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_text_without_bytes_does_not_raise_type_error(self) -> None:
        provider = LocalExtractOCRProvider()
        result = await provider.extract_text(
            object_ref=StoredObject(bucket="synthetic", key="fixture.pdf"),
            content_type="application/pdf",
        )
        self.assertEqual(result.pages, [])
        self.assertEqual(result.provider, "local_extract")

    async def test_extract_layout_accepts_base_provider_optional_argument(self) -> None:
        provider = LocalExtractOCRProvider()
        result = await provider.extract_layout(
            object_ref=StoredObject(bucket="synthetic", key="fixture.pdf"),
            content_type="application/pdf",
        )
        self.assertEqual(result.pages, [])

    async def test_real_synthetic_pdf_bytes_are_extracted(self) -> None:
        stream = io.BytesIO()
        pdf = Canvas(stream)
        pdf.drawString(72, 720, "SYNTHETIC OCR CONTRACT")
        pdf.save()
        result = await LocalExtractOCRProvider().extract_layout(
            object_ref=StoredObject(bucket="synthetic", key="fixture.pdf"),
            content_type="application/pdf",
            page_bytes=stream.getvalue(),
        )
        self.assertEqual(len(result.pages), 1)
        self.assertIn("SYNTHETIC OCR CONTRACT", result.pages[0].text)
