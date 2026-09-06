from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_privacy_and_restore_drills_write_evidence() -> None:
    from app.scripts import run_privacy_drill, run_restore_drill

    with pytest.raises(SystemExit) as ei:
        run_privacy_drill.main()
    assert ei.value.code == 0
    run_restore_drill.main()
    root = Path(__file__).resolve().parents[3]
    deletion = root / "artifacts" / "drills" / "deletion_log_canary.json"
    restore = root / "artifacts" / "drills" / "restore_dry_run.json"
    assert deletion.exists()
    assert restore.exists()
    d = json.loads(deletion.read_text(encoding="utf-8"))
    assert d["log_canary_safe"] is True
    r = json.loads(restore.read_text(encoding="utf-8"))
    assert r["signed_off"] is False
