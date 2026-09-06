"""Helpers that keep sensitive document content out of logs/errors."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager

# Filenames can contain whitespace, delimiters and newlines. Fail closed by
# redacting the rest of the message instead of assuming a single-token value.
_FILENAME_RE = re.compile(r"(?is)(filename|original_name|display_name)\s*[:=].*")
_QUOTE_RE = re.compile(r"[«»\"'].{20,}[«»\"']")


class DocumentSafeFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # Interpolate first: sensitive values may live in positional or
            # mapping arguments rather than in the logging format string.
            msg = record.getMessage()
        except (TypeError, ValueError):
            record.msg = "document_log_format_error"
            record.args = ()
            return True
        record.args = ()
        # Never allow obvious extracted-text dumps, including interpolated ones.
        if "extracted_text" in msg.lower() or "ocr_text" in msg.lower():
            record.msg = "document_content_refused_in_logs"
            return True
        msg = _FILENAME_RE.sub(r"\1=[REDACTED_FILENAME]", msg)
        record.msg = _QUOTE_RE.sub("[REDACTED_QUOTE]", msg)
        return True


@contextmanager
def safe_error_payload[T](base: dict[str, T]) -> Iterator[dict[str, T]]:
    """Strip fields that must never leave the trust boundary via error bodies."""
    forbidden = {"filename", "original_filename", "extracted_text", "quote", "text", "ocr_text", "risk_score"}
    yield {k: v for k, v in base.items() if k not in forbidden}
