"""Synthetic asset checks, not official-form or font-rendering acceptance."""

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.services.forms.fill import fonts


class FontManifestSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.assets = self.root / "Ресурсы шрифта"
        self.assets.mkdir()
        self.font = self.assets / "NotoSans-Regular.ttf"
        self.font.write_bytes(b"synthetic font asset, not a renderable font")
        self.license = self.assets / "LICENSE"
        self.license.write_text("SIL OPEN FONT LICENSE Version 1.1", encoding="utf-8")
        self.manifest = self.assets / "font-manifest.json"
        self.valid = {
            "filename": self.font.name,
            "license_file": self.license.name,
            "expected_sha256": hashlib.sha256(self.font.read_bytes()).hexdigest(),
        }
        self.write_manifest(self.valid)
        self.enterContext(patch.object(fonts, "ASSETS", self.assets))
        self.enterContext(patch.object(fonts, "MANIFEST", self.manifest))

    def write_manifest(self, value: object) -> None:
        self.manifest.write_text(json.dumps(value), encoding="utf-8")

    def assert_blocked(self) -> None:
        status = fonts.bundled_font_status()
        self.assertFalse(status.ok)
        self.assertTrue(status.reason)
        with self.assertRaises(FileNotFoundError):
            fonts.resolve_allowed_font()

    def test_valid_bundled_assets_in_unicode_directory(self) -> None:
        self.assertTrue(fonts.bundled_font_status().ok)
        self.assertEqual(fonts.resolve_allowed_font(), self.font)
        self.assertEqual(fonts.font_hash(), self.valid["expected_sha256"])

    def test_non_object_and_non_string_entries_are_rejected(self) -> None:
        for value in [None, [], "manifest", 42, {**self.valid, "filename": []}, {**self.valid, "note": False}]:
            with self.subTest(value=value):
                self.write_manifest(value)
                self.assert_blocked()

    def test_malformed_json_and_encoding_are_rejected(self) -> None:
        for raw in [b"{", b"\xff"]:
            with self.subTest(raw=raw):
                self.manifest.write_bytes(raw)
                self.assert_blocked()

    def test_paths_outside_bundle_are_rejected(self) -> None:
        for field in ["filename", "license_file"]:
            names = ["../outside", "/outside", "C:\\outside", "C:outside", "\\\\host\\share", "x:stream", ".."]
            for name in names:
                with self.subTest(field=field, name=name):
                    self.write_manifest({**self.valid, field: name})
                    self.assert_blocked()

    def test_resolved_outside_target_is_rejected(self) -> None:
        # Mock only filesystem resolution so this guard runs on Windows without
        # requiring developer mode or elevated symlink-creation privileges.
        original = Path.resolve
        target = self.font
        outside = self.root / "outside.ttf"

        def resolve(path: Path, strict: bool = False) -> Path:
            if path == target:
                return outside
            return original(path, strict=strict)

        with patch.object(Path, "resolve", resolve):
            self.assert_blocked()

    def test_missing_manifest_does_not_allow_system_fallback(self) -> None:
        self.manifest.unlink()
        self.assert_blocked()

    def test_changed_font_hash_is_rejected(self) -> None:
        self.font.write_bytes(b"modified")
        self.assert_blocked()

    def test_missing_or_wrong_license_is_rejected(self) -> None:
        self.license.write_text("Not a licensed asset", encoding="utf-8")
        self.assert_blocked()
        self.license.unlink()
        self.assert_blocked()

    def test_unreadable_manifest_returns_safe_status(self) -> None:
        with patch.object(Path, "read_text", side_effect=PermissionError("private path")):
            self.assert_blocked()
            self.assertNotIn("private path", fonts.bundled_font_status().reason)


if __name__ == "__main__":
    unittest.main()
