"""Real full-profile backup tests; mocks only inject failures, never success."""

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


class ProfileBackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = self.root / "Данные пользователя's"
        self.program = self.root / "Программа Docly"
        self.backups = self.root / "Резервные копии"
        self.profile.mkdir()
        self.program.mkdir()
        for name in ["documents", "attachments", "templates", "empty directory"]:
            (self.profile / name).mkdir()
        for name in ["settings.json", "documents/документ.txt", "attachments/scan.bin", "templates/мой шаблон.txt"]:
            (self.profile / name).write_bytes(b"synthetic-profile-data\x00\xff")
        with closing(sqlite3.connect(self.profile / "docly.db")) as db:
            db.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, text TEXT NOT NULL)")
            db.execute("INSERT INTO records VALUES (1, 'synthetic@example.invalid')")
            db.commit()

    def backup(self, **kwargs) -> Path:
        return create_profile_backup(self.profile, self.backups, program_dir=self.program, **kwargs)

    def hashes(self) -> dict[str, bytes]:
        return {p.relative_to(self.profile).as_posix(): p.read_bytes() for p in self.profile.rglob("*") if p.is_file()}

    def assert_no_published_snapshot(self) -> None:
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_every_file_empty_directory_and_sqlite_image_are_verified(self) -> None:
        original = self.hashes()
        snapshot = self.backup()
        manifest = verify_profile_backup(snapshot)
        self.assertEqual(set(manifest["files"]), set(original))
        self.assertIn("empty directory", manifest["directories"])
        for name, data in original.items():
            self.assertEqual((snapshot / "profile" / name).read_bytes(), data)
        with closing(sqlite3.connect(snapshot / "sqlite" / "docly.db")) as db:
            self.assertEqual(db.execute("SELECT * FROM records").fetchall(), [(1, "synthetic@example.invalid")])
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
        self.assertEqual(self.hashes(), original)

    def test_successful_snapshots_are_never_overwritten_or_deleted(self) -> None:
        first = self.backup()
        second = self.backup()
        self.assertNotEqual(first, second)
        verify_profile_backup(first)
        verify_profile_backup(second)

    def test_wal_committed_rows_are_in_consistent_image(self) -> None:
        with closing(sqlite3.connect(self.profile / "docly.db")) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA wal_autocheckpoint=0")
            db.execute("INSERT INTO records VALUES (2, 'committed WAL')")
            db.commit()
            self.assertTrue((self.profile / "docly.db-wal").exists())
            original = self.hashes()
            snapshot = self.backup()
            self.assertEqual(self.hashes(), original)
            manifest = verify_profile_backup(snapshot)
            self.assertIn("docly.db-wal", manifest["files"])
            self.assertIn("docly.db-shm", manifest["files"])
            with closing(sqlite3.connect(snapshot / "sqlite" / "docly.db")) as copy:
                self.assertEqual(copy.execute("SELECT id FROM records ORDER BY id").fetchall(), [(1,), (2,)])

    def test_corrupt_database_aborts_and_preserves_source(self) -> None:
        (self.profile / "docly.db").write_bytes(b"not a database")
        original = self.hashes()
        with self.assertRaises(ProfileBackupError):
            self.backup()
        self.assertEqual(self.hashes(), original)
        self.assert_no_published_snapshot()

    def test_copy_failure_aborts_and_preserves_source(self) -> None:
        original = self.hashes()
        with patch("app.profile_backup.shutil.copy2", side_effect=OSError("injected copy failure")):
            with self.assertRaises(OSError):
                self.backup()
        self.assertEqual(self.hashes(), original)
        self.assert_no_published_snapshot()

    def test_sqlite_timeout_removes_incomplete_snapshot(self) -> None:
        original = self.hashes()
        # Inject only elapsed time; filesystem and SQLite backup remain real.
        # A sub-clock-resolution timeout is nondeterministic on Windows.
        with patch("app.profile_backup.time.monotonic", side_effect=[100.0, 161.0]):
            with self.assertRaises(TimeoutError):
                self.backup(sqlite_timeout=60.0)
        self.assertEqual(self.hashes(), original)
        self.assert_no_published_snapshot()

    def test_changed_source_aborts_instead_of_publishing_inconsistent_profile(self) -> None:
        real_copy = shutil.copy2

        def changing_copy(source, destination, **kwargs):
            result = real_copy(source, destination, **kwargs)
            (self.profile / "late-file.txt").write_text("synthetic concurrent change")
            return result

        with patch("app.profile_backup.shutil.copy2", side_effect=changing_copy):
            with self.assertRaisesRegex(ProfileBackupError, "changed"):
                self.backup()
        self.assert_no_published_snapshot()

    def test_backup_inside_program_or_profile_is_rejected(self) -> None:
        for root in [self.profile / "backups", self.program / "backups", self.profile, self.root]:
            with self.subTest(root=root):
                with self.assertRaises(ProfileBackupError):
                    create_profile_backup(self.profile, root, program_dir=self.program)

    def test_insufficient_space_is_blocking(self) -> None:
        usage = shutil.disk_usage(self.root)
        with patch("app.profile_backup.shutil.disk_usage", return_value=type(usage)(usage.total, usage.total, 0)):
            with self.assertRaisesRegex(ProfileBackupError, "space"):
                self.backup()
        self.assert_no_published_snapshot()

    def test_file_tampering_is_detected(self) -> None:
        snapshot = self.backup()
        (snapshot / "profile" / "settings.json").write_bytes(b"tampered")
        with self.assertRaises(ProfileBackupError):
            verify_profile_backup(snapshot)

    def test_missing_file_is_detected(self) -> None:
        snapshot = self.backup()
        (snapshot / "profile" / "attachments" / "scan.bin").unlink()
        with self.assertRaises(ProfileBackupError):
            verify_profile_backup(snapshot)

    def test_sqlite_image_tampering_is_detected(self) -> None:
        snapshot = self.backup()
        (snapshot / "sqlite" / "docly.db").write_bytes(b"tampered")
        with self.assertRaises(ProfileBackupError):
            verify_profile_backup(snapshot)

    def test_manifest_path_traversal_is_rejected(self) -> None:
        snapshot = self.backup()
        path = snapshot / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["sqlite_images"]["../outside.db"] = {"size": 0, "sha256": "0" * 64}
        path.write_text(json.dumps(manifest))
        with self.assertRaises(ProfileBackupError):
            verify_profile_backup(snapshot)

    def test_omitted_sqlite_image_is_detected(self) -> None:
        snapshot = self.backup()
        path = snapshot / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["sqlite_images"] = {}
        path.write_text(json.dumps(manifest))
        with self.assertRaises(ProfileBackupError):
            verify_profile_backup(snapshot)

    def test_invalid_time_budget_is_rejected(self) -> None:
        for value in [0, -1, float("nan"), float("inf")]:
            with self.subTest(value=value):
                with self.assertRaises(ProfileBackupError):
                    self.backup(sqlite_timeout=value)

    def test_valid_header_with_corrupt_pages_aborts(self) -> None:
        db = self.profile / "docly.db"
        data = bytearray(db.read_bytes())
        data[100:150] = bytes(50)
        db.write_bytes(data)
        with self.assertRaises((sqlite3.DatabaseError, ProfileBackupError)):
            self.backup()
        self.assert_no_published_snapshot()


if __name__ == "__main__":
    unittest.main()
