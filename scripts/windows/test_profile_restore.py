"""Real restore staging regressions; no activation or installer acceptance."""
from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from app.profile_backup import ProfileBackupError, create_profile_backup, verify_profile_backup
from profile_restore import stage_profile_restore


class ProfileRestoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = self.root / "Данные's"
        self.program = self.root / "Program"
        self.profile.mkdir()
        self.program.mkdir()
        (self.profile / "empty").mkdir()
        (self.profile / "settings.json").write_bytes(b"synthetic settings")
        (self.profile / "notes-wal").write_bytes(b"not a database sidecar")
        with closing(sqlite3.connect(self.profile / "docly.db")) as db:
            db.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT)")
            db.execute("INSERT INTO records VALUES (1, 'original')")
            db.commit()
        self.backups = self.root / "Backups"

    def backup(self) -> Path:
        return create_profile_backup(self.profile, self.backups, program_dir=self.program)

    def stage(self, snapshot: Path) -> Path:
        return stage_profile_restore(snapshot, profile_dir=self.profile, program_dir=self.program)

    def tree(self, root: Path) -> dict[str, bytes]:
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def test_complete_restore_stage_never_changes_live_profile_or_archive(self) -> None:
        snapshot = self.backup()
        archive = self.tree(snapshot)
        (self.profile / "settings.json").write_bytes(b"new version settings")
        (self.profile / "new-document").write_bytes(b"must not be deleted")
        live = self.tree(self.profile)
        restored = self.stage(snapshot)
        self.assertEqual(restored.parent, self.profile.parent)
        self.assertEqual((restored / "settings.json").read_bytes(), b"synthetic settings")
        self.assertTrue((restored / "empty").is_dir())
        self.assertEqual((restored / "notes-wal").read_bytes(), b"not a database sidecar")
        self.assertNotIn("new-document", self.tree(restored))
        self.assertEqual(self.tree(snapshot), archive)
        self.assertEqual(self.tree(self.profile), live)

    def test_consistent_wal_image_is_restored_without_replaying_raw_sidecars(self) -> None:
        with closing(sqlite3.connect(self.profile / "docly.db")) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA wal_autocheckpoint=0")
            db.execute("INSERT INTO records VALUES (2, 'committed WAL')")
            db.commit()
            snapshot = self.backup()
            archive = self.tree(snapshot)
            self.assertIn("profile/docly.db-wal", archive)
            restored = self.stage(snapshot)
            self.assertFalse((restored / "docly.db-wal").exists())
            self.assertFalse((restored / "docly.db-shm").exists())
            with closing(sqlite3.connect(restored / "docly.db")) as copy:
                self.assertEqual(copy.execute("SELECT * FROM records ORDER BY id").fetchall(),
                                 [(1, "original"), (2, "committed WAL")])
                self.assertEqual(copy.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
            self.assertEqual(self.tree(snapshot), archive)

    def test_retries_create_distinct_stages_without_overwriting_previous_stage(self) -> None:
        snapshot = self.backup()
        first = self.stage(snapshot)
        content = self.tree(first)
        second = self.stage(snapshot)
        self.assertNotEqual(first, second)
        self.assertEqual(self.tree(first), content)
        self.assertEqual(self.tree(second), content)
        verify_profile_backup(snapshot)

    def test_copy_failure_preserves_live_and_archive_and_removes_only_owned_stage(self) -> None:
        snapshot = self.backup()
        live, archive = self.tree(self.profile), self.tree(snapshot)
        sentinel = self.root / ".docly-restore-user-owned"
        sentinel.mkdir()
        (sentinel / "keep").write_bytes(b"keep")
        with patch("profile_restore.shutil.copy2", side_effect=OSError("injected disk failure")):
            with self.assertRaises(OSError):
                self.stage(snapshot)
        self.assertEqual(list(self.root.glob(".docly-restore-*")), [sentinel])
        self.assertEqual((sentinel / "keep").read_bytes(), b"keep")
        self.assertEqual(self.tree(self.profile), live)
        self.assertEqual(self.tree(snapshot), archive)

    def test_corrupted_snapshot_is_rejected_before_creating_stage(self) -> None:
        snapshot = self.backup()
        (snapshot / "profile" / "settings.json").write_bytes(b"tampered")
        live = self.tree(self.profile)
        with self.assertRaises(ProfileBackupError):
            self.stage(snapshot)
        self.assertEqual(list(self.root.glob(".docly-restore-*")), [])
        self.assertEqual(self.tree(self.profile), live)

    def test_restore_volume_free_space_is_checked_before_copying(self) -> None:
        snapshot = self.backup()
        usage = shutil.disk_usage(self.root)
        with patch("profile_restore.shutil.disk_usage", return_value=type(usage)(usage.total, usage.total, 0)) as check:
            with self.assertRaisesRegex(ProfileBackupError, "space"):
                self.stage(snapshot)
        check.assert_called_once_with(self.profile.parent)
        self.assertEqual(list(self.root.glob(".docly-restore-*")), [])

    def test_copy_corruption_is_detected(self) -> None:
        snapshot = self.backup()
        real_copy = shutil.copy2

        def corrupt(source, target, **kwargs):
            result = real_copy(source, target, **kwargs)
            if Path(target).name == "settings.json":
                Path(target).write_bytes(b"copy corruption")
            return result

        with patch("profile_restore.shutil.copy2", side_effect=corrupt):
            with self.assertRaisesRegex(ProfileBackupError, "checksum"):
                self.stage(snapshot)
        self.assertEqual(list(self.root.glob(".docly-restore-*")), [])
        verify_profile_backup(snapshot)

    def test_flush_failure_is_blocking(self) -> None:
        snapshot = self.backup()
        with patch("profile_restore._flush", side_effect=OSError("injected flush failure")):
            with self.assertRaises(OSError):
                self.stage(snapshot)
        self.assertEqual(list(self.root.glob(".docly-restore-*")), [])
        verify_profile_backup(snapshot)

    def test_overlapping_profile_program_or_snapshot_is_rejected(self) -> None:
        snapshot = self.backup()
        for profile, program in [(snapshot / "child", self.program),
                                 (snapshot.parent, self.program),
                                 (self.profile, self.profile / "program"),
                                 (self.program / "profile", self.program)]:
            with self.subTest(profile=profile, program=program):
                with self.assertRaises(ProfileBackupError):
                    stage_profile_restore(snapshot, profile_dir=profile, program_dir=program)

    def test_missing_profile_can_be_staged_without_being_created(self) -> None:
        snapshot = self.backup()
        missing = self.root / "Missing profile"
        stage = stage_profile_restore(snapshot, profile_dir=missing, program_dir=self.program)
        self.assertFalse(missing.exists())
        self.assertEqual((stage / "settings.json").read_bytes(), b"synthetic settings")

    def test_manifest_traversal_never_writes_outside_stage(self) -> None:
        snapshot = self.backup()
        manifest_path = snapshot / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["directories"].append("../escape")
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(ProfileBackupError):
            self.stage(snapshot)
        self.assertFalse((self.root / "escape").exists())
        self.assertEqual(list(self.root.glob(".docly-restore-*")), [])


if __name__ == "__main__":
    unittest.main()
