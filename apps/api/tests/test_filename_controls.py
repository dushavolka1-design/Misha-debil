from __future__ import annotations

import unittest

from app.services.upload.filename import sanitize_display_filename


class FilenameControlTests(unittest.TestCase):
    def test_each_bidi_control_is_removed_not_replaced(self) -> None:
        for codepoint in (0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069, 0x200E, 0x200F):
            with self.subTest(codepoint=hex(codepoint)):
                self.assertEqual(sanitize_display_filename(f"invoice{chr(codepoint)}.pdf"), "invoice.pdf")

    def test_only_controls_use_fallback(self) -> None:
        self.assertEqual(sanitize_display_filename("\u202e\u2069"), "document")

    def test_path_separators_and_ascii_controls_remain_sanitized(self) -> None:
        self.assertEqual(sanitize_display_filename("../a\\b\x00.pdf"), "_a_b.pdf")

    def test_ordinary_label_is_unchanged(self) -> None:
        self.assertEqual(sanitize_display_filename("invoice (2).pdf"), "invoice (2).pdf")

    def test_length_bound_preserves_extension(self) -> None:
        label = sanitize_display_filename("a" * 200 + ".pdf")
        self.assertEqual(len(label), 180)
        self.assertTrue(label.endswith(".pdf"))
