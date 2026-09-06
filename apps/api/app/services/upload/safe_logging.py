"""Helpers that keep sensitive document content out of logs/errors."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager

_FILENAME_RE = re.compile(r"(?i)(filename|original_name|display_name)\s*[:=]\s*\S+")
_QUOTE_RE = re.compile(r"[«»\"'].{20,}[«»\"']")


class DocumentSafeFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.msg)
        msg = _FILENAME_RE.sub(r"\1=[REDACTED_FILENAME]", msg)
        msg = _QUOTE_RE.sub("[REDACTED_QUOTE]", msg)
        # Never allow obvious extracted-text dumps
        if "extracted_text" in msg.lower() or "ocr_text" in msg.lower():
            record.msg = "document_content_refused_in_logs"
            record.args = ()
            return True
        record.msg = msg
        return True


@contextmanager
def safe_error_payload(base: dict) -> Iterator[dict]:
    """Strip fields that must never leave the trust boundary via error bodies."""
    forbidden = {"filename", "original_filename", "extracted_text", "quote", "text", "ocr_text", "risk_score"}
    yield {k: v for k, v in base.items() if k not in forbidden}
