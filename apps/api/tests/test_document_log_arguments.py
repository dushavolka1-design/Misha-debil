from __future__ import annotations

import logging
import unittest

from app.services.upload.safe_logging import DocumentSafeFilter, safe_error_payload


class DocumentLogArgumentTests(unittest.TestCase):
    def filtered(self, msg: str, args: tuple[object, ...] | dict[str, object]) -> logging.LogRecord:
        record_args = (args,) if isinstance(args, dict) else args
        record = logging.LogRecord("synthetic", logging.INFO, __file__, 1, msg, record_args, None)
        self.assertTrue(DocumentSafeFilter().filter(record))
        return record

    def test_positional_filename_is_redacted_after_formatting(self) -> None:
        record = self.filtered("upload filename=%s", ("synthetic private.pdf",))
        self.assertEqual(record.getMessage(), "upload filename=[REDACTED_FILENAME]")
        self.assertEqual(record.args, ())

    def test_mapping_filename_is_redacted(self) -> None:
        record = self.filtered("upload original_name=%(name)s", {"name": "synthetic.pdf"})
        self.assertNotIn("synthetic.pdf", record.getMessage())
        self.assertEqual(record.args, ())

    def test_filename_with_delimiters_and_newline_is_not_partially_logged(self) -> None:
        record = self.filtered("display_name=%s", ("synthetic; private\nsecond line.pdf",))
        self.assertEqual(record.getMessage(), "display_name=[REDACTED_FILENAME]")

    def test_interpolated_extracted_content_is_refused(self) -> None:
        record = self.filtered("%s", ("ocr_text=synthetic document contents",))
        self.assertEqual(record.getMessage(), "document_content_refused_in_logs")
        self.assertEqual(record.args, ())

    def test_integer_formatting_is_preserved(self) -> None:
        self.assertEqual(self.filtered("processed %d pages", (3,)).getMessage(), "processed 3 pages")

    def test_malformed_format_fails_closed_without_logging_arguments(self) -> None:
        record = self.filtered("processed %d", ("synthetic confidential value",))
        self.assertEqual(record.getMessage(), "document_log_format_error")
        self.assertEqual(record.args, ())

    def test_safe_payload_keeps_values_and_does_not_mutate_input(self) -> None:
        base = {"code": "upload_failed", "filename": "synthetic.pdf"}
        with safe_error_payload(base) as payload:
            self.assertEqual(payload, {"code": "upload_failed"})
        self.assertEqual(base["filename"], "synthetic.pdf")
