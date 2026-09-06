"""Verified whole-profile snapshots. Call only after all profile writers stop.

Raw files (including WAL/SHM) are retained for audit; consistent SQLite backup-API
images are stored separately. A snapshot is published only after every file and
SQLite image verifies. This module does not implement installer rollback.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import sqlite3
import stat
import tempfile
import time
from contextlib import closing
from pathlib import Path
from typing import TypedDict, cast
from uuid import uuid4


class FileDigest(TypedDict):
    size: int
    sha256: str


class BackupManifest(TypedDict):
    format: int
    directories: list[str]
    files: dict[str, FileDigest]
    sqlite_images: dict[str, FileDigest]


class ProfileBackupError(RuntimeError):
    """A snapshot cannot be trusted; the caller must not start an upgrade."""


def _hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _plain(path: Path) -> os.stat_result:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ProfileBackupError("Links and reparse points are not supported in profile backups")
    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
        raise ProfileBackupError("Profile contains a non-regular filesystem entry")
    return info


def _checked_root(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            _plain(item)
    return path


def _inventory(root: Path) -> tuple[list[str], dict[str, FileDigest]]:
    directories: list[str] = []
    files: dict[str, FileDigest] = {}
    _plain(root)
    for parent, subdirs, names in os.walk(root, followlinks=False):
        for name in sorted(subdirs + names):
            path = Path(parent) / name
            info = _plain(path)
            relative = path.relative_to(root).as_posix()
            if stat.S_ISDIR(info.st_mode):
                directories.append(relative)
            else:
                files[relative] = {"size": info.st_size, "sha256": _hash(path)}
    return sorted(directories), dict(sorted(files.items()))


def _integrity(path: Path) -> None:
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ProfileBackupError("SQLite snapshot integrity check failed")


def _sqlite_image(source: Path, destination: Path, deadline: float) -> None:
    def progress(_status: int, _remaining: int, _total: int) -> None:
        if time.monotonic() >= deadline:
            raise TimeoutError("Profile SQLite snapshot exceeded its time budget")

    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=1)) as original:
        with closing(sqlite3.connect(destination)) as copy:
            original.backup(copy, pages=256, progress=progress, sleep=0.05)
    _integrity(destination)


def _relative(root: Path, name: str) -> Path:
    # Manifests are data, not permission to read arbitrary paths.
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ProfileBackupError("Invalid snapshot entry")
    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ProfileBackupError("Invalid snapshot entry")
    path = root.joinpath(*parts)
    if not path.is_relative_to(root):
        raise ProfileBackupError("Snapshot entry escapes its root")
    return path


def verify_profile_backup(snapshot: Path) -> BackupManifest:
    snapshot = _checked_root(snapshot)
    try:
        _plain(snapshot / "manifest.json")
        manifest = cast(BackupManifest, json.loads((snapshot / "manifest.json").read_text(encoding="utf-8")))
        if manifest["format"] != 1:
            raise ProfileBackupError("Unsupported snapshot format")
        directories, files = _inventory(snapshot / "profile")
        if directories != manifest["directories"] or files != manifest["files"]:
            raise ProfileBackupError("Profile snapshot file inventory or checksum mismatch")
        expected_databases = set()
        for relative in files:
            with _relative(snapshot / "profile", relative).open("rb") as stream:
                if stream.read(16) == b"SQLite format 3\x00":
                    expected_databases.add(relative)
        if set(manifest["sqlite_images"]) != expected_databases:
            raise ProfileBackupError("SQLite image inventory is incomplete")
        for relative, expected in manifest["sqlite_images"].items():
            if relative not in files:
                raise ProfileBackupError("SQLite image has no corresponding profile file")
            image = _relative(snapshot / "sqlite", relative)
            _checked_root(image)
            if image.stat().st_size != expected["size"] or _hash(image) != expected["sha256"]:
                raise ProfileBackupError("SQLite image checksum mismatch")
            _integrity(image)
        return manifest
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        raise ProfileBackupError("Profile backup verification failed") from exc


def create_profile_backup(
    profile: Path,
    backup_root: Path,
    *,
    program_dir: Path,
    sqlite_timeout: float = 60.0,
) -> Path:
    """Snapshot all profile files, fail closed, and retain successful snapshots.

    Requires a stopped profile. Rejects symlinks/junctions rather than following
    them out of the approved data tree. Backup root must be outside both profile
    and program trees. Caller must abort the update on any exception.
    """
    profile = _checked_root(profile)
    backup_root = _checked_root(backup_root)
    program_dir = _checked_root(program_dir)
    if not math.isfinite(sqlite_timeout) or sqlite_timeout <= 0 or not profile.is_dir():
        raise ProfileBackupError("Existing profile and positive SQLite time budget required")
    for protected in (profile, program_dir):
        if backup_root.is_relative_to(protected) or protected.is_relative_to(backup_root):
            raise ProfileBackupError("Backup root must be separate from data and program trees")
    before_dirs, before_files = _inventory(profile)
    backup_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    required = 2 * sum(int(f["size"]) for f in before_files.values()) + 16 * 1024 * 1024
    if shutil.disk_usage(backup_root).free < required:
        raise ProfileBackupError("Insufficient space for a verified full profile snapshot")
    stage = Path(tempfile.mkdtemp(prefix=".incomplete-", dir=backup_root))
    final = backup_root / ("profile-" + uuid4().hex)
    try:
        raw_root = stage / "profile"
        raw_root.mkdir()
        for relative in before_dirs:
            _relative(raw_root, relative).mkdir()
        images: dict[str, FileDigest] = {}
        databases: list[str] = []
        for relative, expected in before_files.items():
            source = _relative(profile, relative)
            target = _relative(raw_root, relative)
            _plain(source)
            shutil.copy2(source, target, follow_symlinks=False)
            _plain(target)
            if target.stat().st_size != expected["size"] or _hash(target) != expected["sha256"]:
                raise ProfileBackupError("Profile changed while copying")
            with target.open("rb") as stream:
                is_sqlite = stream.read(16) == b"SQLite format 3\x00"
            if is_sqlite:
                databases.append(relative)
            elif relative == "docly.db":
                raise ProfileBackupError("Docly database is empty or has an invalid SQLite header")
        if _inventory(profile) != (before_dirs, before_files):
            raise ProfileBackupError("Profile changed during backup; stop all writers and retry")
        # Even mode=ro can modify SHM read marks: open only disposable DB/WAL copies.
        for relative in databases:
            image = _relative(stage / "sqlite", relative)
            image.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=stage) as scratch:
                source_copy = Path(scratch) / "database.db"
                shutil.copy2(_relative(raw_root, relative), source_copy)
                wal = _relative(raw_root, relative + "-wal")
                if wal.exists():
                    shutil.copy2(wal, Path(str(source_copy) + "-wal"))
                _sqlite_image(source_copy, image, time.monotonic() + sqlite_timeout)
            images[relative] = {"size": image.stat().st_size, "sha256": _hash(image)}
        manifest: BackupManifest = {
            "format": 1, "directories": before_dirs, "files": before_files, "sqlite_images": images
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        verify_profile_backup(stage)
        for path in stage.rglob("*"):
            if path.is_file():
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
        stage.rename(final)
        return final
    except BaseException:
        shutil.rmtree(stage)
        raise
