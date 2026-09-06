"""Strict, portable local-object inventory for the offline desktop importer."""
from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path, PurePosixPath


class MigrationError(RuntimeError):
    """Safe diagnostic code; never includes database credentials or row contents."""


def object_name(value: str) -> str:
    parts = PurePosixPath(value).parts
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{p}{n}" for p in ("COM", "LPT") for n in range(1, 10)}
    if not parts or value != "/".join(parts):
        raise MigrationError("noncanonical_object_path")
    for part in parts:
        if (part in {".", ".."} or part.endswith((".", " "))
                or any(ord(c) < 32 or c in '<>:"\\|?*' for c in part)
                or part.split(".")[0].upper() in reserved):
            raise MigrationError("nonportable_object_path")
    return value


def _plain(path: Path, *, directory: bool) -> None:
    info = path.lstat()
    reparse = getattr(info, "st_file_attributes", 0) & 0x400
    if reparse or stat.S_ISLNK(info.st_mode):
        raise MigrationError("linked_object_rejected")
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise MigrationError("object_directory_required")
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise MigrationError("nonregular_object_rejected")


def digest_file(path: Path) -> tuple[int, str]:
    _plain(path, directory=False)
    before = path.stat()
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        opened = os.fstat(source.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise MigrationError("object_changed")
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise MigrationError("object_changed")
    return size, digest.hexdigest()


def inventory(root: Path) -> dict[str, tuple[int, str]]:
    _plain(root, directory=True)
    result: dict[str, tuple[int, str]] = {}
    names: set[str] = set()
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories + files):
            path = Path(parent) / name
            relative = object_name(path.relative_to(root).as_posix())
            folded = relative.casefold()
            if folded in names:
                raise MigrationError("case_colliding_objects")
            names.add(folded)
            _plain(path, directory=name in directories)
            if name in files:
                result[relative] = digest_file(path)
    return result


def copy_inventory(root: Path, target: Path, expected: dict[str, tuple[int, str]]) -> None:
    target.mkdir()
    for relative, fingerprint in expected.items():
        source = root / relative
        _plain(source, directory=False)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as reader, destination.open("xb") as writer:
            for chunk in iter(lambda: reader.read(1024 * 1024), b""):
                writer.write(chunk)
            writer.flush()
            os.fsync(writer.fileno())
        if digest_file(destination) != fingerprint:
            raise MigrationError("copied_object_mismatch")
    if inventory(root) != expected or inventory(target) != expected:
        raise MigrationError("object_inventory_changed")
