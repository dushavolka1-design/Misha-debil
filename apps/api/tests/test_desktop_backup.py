"""Real SQLite/filesystem regression tests; no application services or mocks."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app.desktop_backup import backup_before_schema_change


class DesktopBackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Данные Docly's"
        self.root.mkdir()
        self.db = self.root / "docly.db"

    def snapshot(self, **kwargs) -> Path | None:
        return backup_before_schema_change(
            self.db,
            required_tables={"users"},
            required_columns={"users": {"display_name", "avatar_jpeg"}},
            **kwargs,
        )

    def create_old_database(self) -> None:
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)")
            conn.execute("INSERT INTO users VALUES (1, 'person@example.invalid')")
            conn.commit()

    def test_first_install_does_not_create_database_or_backup(self) -> None:
        self.assertIsNone(self.snapshot())
        self.assertFalse(self.db.exists())
        self.assertFalse((self.root / "backups").exists())

    def test_old_schema_snapshot_survives_real_schema_upgrade(self) -> None:
        self.create_old_database()
        original = self.db.read_bytes()
        settings = self.root / "settings.json"
        settings.write_text('{"theme":"dark"}', encoding="utf-8")
        objects = self.root / "objects"
        objects.mkdir()
        (objects / "document.bin").write_bytes(b"user document bytes")
        backup = self.snapshot()
        self.assertIsNotNone(backup)
        self.assertEqual(self.db.read_bytes(), original)
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("ALTER TABLE users ADD COLUMN display_name VARCHAR(80)")
            conn.execute("ALTER TABLE users ADD COLUMN avatar_jpeg BLOB")
            conn.commit()
            self.assertEqual(conn.execute("SELECT email FROM users").fetchone()[0],
                             "person@example.invalid")
        with closing(sqlite3.connect(backup)) as conn:
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone(), ("ok",))
            self.assertEqual(conn.execute("SELECT * FROM users").fetchall(),
                             [(1, "person@example.invalid")])
        self.assertEqual(settings.read_text(encoding="utf-8"), '{"theme":"dark"}')
        self.assertEqual((objects / "document.bin").read_bytes(), b"user document bytes")
        self.assertIsNone(self.snapshot())
        self.assertEqual(len(list((self.root / "backups").glob("*.db"))), 1)
        self.assertFalse(list((self.root / "backups").glob("*.tmp")))

    def test_committed_wal_pages_are_in_snapshot(self) -> None:
        with closing(sqlite3.connect(self.db)) as writer:
            self.assertEqual(writer.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)")
            writer.execute("INSERT INTO users VALUES (7, 'wal@example.invalid')")
            writer.commit()
            self.assertGreater(Path(str(self.db) + "-wal").stat().st_size, 0)
            backup = self.snapshot()
            with closing(sqlite3.connect(backup)) as reader:
                self.assertEqual(reader.execute("SELECT * FROM users").fetchall(),
                                 [(7, "wal@example.invalid")])

    def test_corrupt_database_is_not_changed(self) -> None:
        damaged = b"not a sqlite database"
        self.db.write_bytes(damaged)
        with self.assertRaisesRegex(RuntimeError, "SQLite"):
            self.snapshot()
        self.assertEqual(self.db.read_bytes(), damaged)
        self.assertFalse((self.root / "backups").exists())

    def test_backup_failure_does_not_change_database(self) -> None:
        self.create_old_database()
        original = self.db.read_bytes()
        (self.root / "backups").write_text("file blocks directory", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.snapshot()
        self.assertEqual(self.db.read_bytes(), original)

    def test_repeated_pending_upgrade_never_overwrites_snapshot(self) -> None:
        self.create_old_database()
        first = self.snapshot()
        second = self.snapshot()
        self.assertNotEqual(first, second)
        self.assertTrue(first.is_file())
        self.assertTrue(second.is_file())

    def test_timeout_preserves_source_and_cleans_partial_backup(self) -> None:
        self.create_old_database()
        original = self.db.read_bytes()
        with self.assertRaises(TimeoutError):
            self.snapshot(timeout=1e-12)
        self.assertEqual(self.db.read_bytes(), original)
        self.assertEqual(list((self.root / "backups").iterdir()), [])

    def test_new_table_also_requires_backup(self) -> None:
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("CREATE TABLE users (display_name TEXT, avatar_jpeg BLOB)")
            conn.commit()
        self.assertIsNone(self.snapshot())
        backup = backup_before_schema_change(
            self.db, required_tables={"users", "documents"}, required_columns={}
        )
        self.assertTrue(backup.is_file())


if __name__ == "__main__":
    unittest.main()
