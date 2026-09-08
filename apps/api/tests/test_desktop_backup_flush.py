"""Flush failure must remain blocking; never remove fsync to make Windows pass."""

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.profile_backup import _flush, create_profile_backup


class BackupFlushTests(unittest.TestCase):
    def test_readonly_copy_is_flushed_with_writable_handle_without_changing_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "readonly.bin"
            path.write_bytes(b"synthetic read-only content")
            path.chmod(stat.S_IREAD)
            mode = path.stat().st_mode
            real_fsync = os.fsync

            def require_writable(fd: int) -> None:
                os.write(fd, b"")
                real_fsync(fd)

            with patch("app.profile_backup.os.fsync", side_effect=require_writable) as sync:
                _flush(path)
                sync.assert_called_once()
            self.assertEqual(path.read_bytes(), b"synthetic read-only content")
            self.assertEqual(path.stat().st_mode, mode)
            path.chmod(mode | stat.S_IWUSR)

    def test_flush_failure_prevents_snapshot_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "data"
            profile.mkdir()
            (profile / "settings.json").write_text("{}")
            with patch("app.profile_backup.os.fsync", side_effect=OSError("injected fsync failure")):
                with self.assertRaisesRegex(OSError, "fsync failure"):
                    create_profile_backup(profile, root / "backups", program_dir=root / "program")
            self.assertEqual(list((root / "backups").iterdir()), [])
            self.assertEqual((profile / "settings.json").read_text(), "{}")
