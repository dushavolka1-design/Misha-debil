from __future__ import annotations

import os

from dar.providers.ports import OCRProvider, OcrDocumentResult, StoredObject


class RuPrivateOCRProvider(OCRProvider):
    """Russian private OCR contour — requires explicit credentials and no-training policy."""

    name = "ru_private_ocr"
    model_version = "ru-private-ocr-v1"

    def __init__(self) -> None:
        self._endpoint = os.environ.get("RU_OCR_ENDPOINT", "").strip()
        self._api_key = os.environ.get("RU_OCR_API_KEY", "").strip()
        self._no_training = os.environ.get("RU_OCR_NO_TRAINING", "").lower() in {"1", "true", "yes"}
        if not self._endpoint or not self._api_key:
            raise RuntimeError(
                "RU_OCR_ENDPOINT and RU_OCR_API_KEY required for ru_private_ocr; "
                "do not send personal data until configured",
            )
        if not self._no_training:
            raise RuntimeError("RU_OCR_NO_TRAINING=true required before sending document bytes")

    async def extract_layout(
        self,
        *,
        object_ref: StoredObject,
        content_type: str,
        page_bytes: bytes | None,
        fixture_id: str | None = None,
    ) -> OcrDocumentResult:
        _ = (object_ref, content_type, page_bytes, fixture_id)
        raise RuntimeError("ru_private_ocr HTTP adapter not wired in this build")
