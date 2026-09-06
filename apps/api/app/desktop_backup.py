"""Verified SQLite snapshots before desktop schema changes (standard library only)."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
from collections.abc import Mapping, Set
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def backup_before_schema_change(
    db_path: Path,
    *,
    required_tables: Set[str],
    required_columns: Mapping[str, Set[str]],
    timeout: float = 30.0,
) -> Path | None:
    """Validate an existing database and snapshot it only when schema work is needed.

    SQLite's backup API includes committed WAL pages, unlike copying docly.db.
    A corrupt source or failed backup aborts the caller before schema changes.
    Snapshots never replace the source, and are retained for manual recovery.
    """
    db_path = db_path.resolve()
    if not db_path.exists() or db_path.stat().st_size == 0:
        return None
    if timeout <= 0:
        raise ValueError("Backup timeout must be positive")
    temporary: Path | None = None
    try:
        with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as source:
            rows = source.execute("PRAGMA integrity_check").fetchall()
            if rows != [("ok",)]:
                raise RuntimeError("SQLite integrity check failed; original database preserved")
            tables = {
                row[0]
                for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            needs_change = not required_tables <= tables
            for table, expected in required_columns.items():
                quoted = '"' + table.replace('"', '""') + '"'
                columns = {row[1] for row in source.execute(f"PRAGMA table_info({quoted})")}
                needs_change = needs_change or not expected <= columns
            if not needs_change:
                return None

            backup_dir = db_path.parent / "backups"
            backup_dir.mkdir(mode=0o700, exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            final = backup_dir / f"docly-before-schema-{stamp}-{uuid4().hex}.db"
            fd, name = tempfile.mkstemp(prefix=".docly-backup-", suffix=".tmp", dir=backup_dir)
            os.close(fd)
            temporary = Path(name)
            deadline = time.monotonic() + timeout

            def progress(_status: int, _remaining: int, _total: int) -> None:
                if time.monotonic() > deadline:
                    raise TimeoutError("SQLite backup timed out; schema was not changed")

            with closing(sqlite3.connect(str(temporary))) as destination:
                source.backup(destination, pages=256, progress=progress, sleep=0.05)
                if destination.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise RuntimeError("SQLite backup verification failed; schema was not changed")
            with temporary.open("rb+") as snapshot:
                os.fsync(snapshot.fileno())
            temporary.replace(final)
            temporary = None
            return final
    except sqlite3.Error as exc:
        raise RuntimeError("SQLite validation/backup failed; original database preserved") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
