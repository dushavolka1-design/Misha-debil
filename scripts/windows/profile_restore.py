"""Prepare a verified restore tree without touching the live profile.

This is a rollback building block, NOT installer integration or activation.
The caller must stop writers and hold its upgrade lock through staging and
activation. Raw snapshot files are never modified, even SQLite WAL/SHM files.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from app.profile_backup import (
    FileDigest,
    ProfileBackupError,
    _checked_root,
    _flush,
    _integrity,
    _inventory,
    _plain,
    _relative,
    verify_profile_backup,
)


def stage_profile_restore(
    snapshot: Path, *, profile_dir: Path, program_dir: Path
) -> Path:
    """Return a newly owned, verified sibling tree; never replace user data.

    Sibling placement allows a later same-volume rename. The live profile and
    program may not contain each other or the snapshot. No existing directory
    is reused and no successful snapshot is removed. On error only this call's
    new temporary tree is cleaned. Free space is checked on the restore volume,
    not on the backup volume. Callers must not activate an unreturned tree.
    """
    snapshot = _checked_root(snapshot)
    profile_dir = _checked_root(profile_dir)
    program_dir = _checked_root(program_dir)
    roots = (snapshot, profile_dir, program_dir)
    for index, root in enumerate(roots):
        for other in roots[index + 1:]:
            if root.is_relative_to(other) or other.is_relative_to(root):
                raise ProfileBackupError("Snapshot, profile and program trees must be separate")
    parent = profile_dir.parent
    if not parent.is_dir() or profile_dir == parent:
        raise ProfileBackupError("An existing non-root profile parent is required")
    if profile_dir.exists() and not profile_dir.is_dir():
        raise ProfileBackupError("Profile target is not a directory")
    manifest = verify_profile_backup(snapshot)
    # A consistent main image already incorporates committed WAL frames.
    # Replaying archived WAL or rollback journals onto it would corrupt/revert
    # the restored database. Keep those bytes only in the immutable raw archive.
    excluded = {
        database + suffix
        for database in manifest["sqlite_images"]
        for suffix in ("-wal", "-shm", "-journal")
    }
    expected: dict[str, FileDigest] = {
        name: digest for name, digest in manifest["files"].items() if name not in excluded
    }
    expected.update(manifest["sqlite_images"])
    required = sum(item["size"] for item in expected.values()) + 16 * 1024 * 1024
    if shutil.disk_usage(parent).free < required:
        raise ProfileBackupError("Insufficient space on profile volume for restore staging")
    stage = Path(tempfile.mkdtemp(prefix=".docly-restore-", dir=parent))
    try:
        for name in manifest["directories"]:
            _relative(stage, name).mkdir()
        for name in expected:
            source_root = snapshot / ("sqlite" if name in manifest["sqlite_images"] else "profile")
            source = _checked_root(_relative(source_root, name))
            _plain(source)
            target = _relative(stage, name)
            shutil.copy2(source, target, follow_symlinks=False)
            _plain(target)
            _flush(target)
        if _inventory(stage) != (manifest["directories"], dict(sorted(expected.items()))):
            raise ProfileBackupError("Restore staging inventory or checksum mismatch")
        for name in manifest["sqlite_images"]:
            _integrity(_relative(stage, name))
        if verify_profile_backup(snapshot) != manifest:
            raise ProfileBackupError("Snapshot changed during restore staging")
        return stage
    except BaseException:
        # This tree was exclusively created by mkdtemp above, never a user path.
        shutil.rmtree(stage)
        raise
