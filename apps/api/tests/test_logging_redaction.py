from __future__ import annotations

import logging

from dar.logging_utils import RedactingFilter
from app.services.upload.safe_logging import DocumentSafeFilter


def test_redacting_filter_masks_secrets() -> None:
    filt = RedactingFilter()
    record = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Authorization: Bearer super-secret-token password=hunter2",
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is True
    assert "super-secret-token" not in record.msg
    assert "hunter2" not in record.msg
    assert "[REDACTED]" in record.msg


def test_redacting_filter_preserves_int_args_for_percent_d() -> None:
    """httpx logs status with %d; stringifying args must not break formatting."""
    filt = RedactingFilter()
    record = logging.LogRecord(
        name="httpx",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='HTTP Request: %s %s "%s %d %s"',
        args=("POST", "http://testserver/x", "HTTP/1.1", 400, "Bad Request"),
        exc_info=None,
    )
    assert filt.filter(record) is True
    assert record.args[3] == 400
    assert isinstance(record.args[3], int)
    assert record.getMessage() == 'HTTP Request: POST http://testserver/x "HTTP/1.1 400 Bad Request"'


def test_document_safe_filter_strips_filename_and_quotes() -> None:
    filt = DocumentSafeFilter()
    record = logging.LogRecord(
        name="api",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg='upload failed filename=secret.pdf quote="очень длинная цитата из документа пользователя здесь"',
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is True
    assert "secret.pdf" not in record.msg
    assert "цитата" not in record.msg
