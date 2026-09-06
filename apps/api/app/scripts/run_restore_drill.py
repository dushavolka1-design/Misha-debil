"""Restore drill dry-run evidence (synthetic). Staging sign-off still required."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timezone
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[4]


def main() -> None:
    out_dir = _root() / "artifacts" / "drills"
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence = {
        "drill": "restore",
        "at": datetime.now(UTC).isoformat(),
        "steps": [
            "snapshot staging postgres volume label",
            "alembic upgrade head on empty DB",
            "alembic downgrade -1 && upgrade head",
            "verify health endpoint",
            "confirm erased objects remain inaccessible (key destruction policy TBD)",
        ],
        "migration_rollback_ci": True,
        "key_hierarchy": "KEY_HIERARCHY_NEEDS_REVIEW",
        "signed_off": False,
        "blocker": "B-05 staging restore drill signed evidence",
    }
    path = out_dir / "restore_dry_run.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
