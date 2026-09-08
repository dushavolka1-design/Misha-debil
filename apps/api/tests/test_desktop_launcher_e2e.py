from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = ROOT / "scripts" / "windows" / "docly_launcher.py"


def _load_launcher():
    spec = importlib.util.spec_from_file_location("docly_launcher", LAUNCHER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_missing_build_fails_in_russian(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_launcher()
    monkeypatch.setattr(mod, "WEB_DIR", tmp_path / "web")
    monkeypatch.setattr(mod, "_venv_python", lambda: Path(sys.executable))
    launcher = mod.DoclyLauncher()
    with pytest.raises(mod.LaunchError) as exc:
        launcher.run()
    assert "интерфейс" in str(exc.value.title).lower() or "собран" in str(exc.value.title).lower()


def test_missing_venv_fails_in_russian(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_launcher()
    monkeypatch.setattr(mod, "_venv_python", lambda: tmp_path / "missing-python.exe")
    launcher = mod.DoclyLauncher()
    with pytest.raises(mod.LaunchError) as exc:
        launcher.run()
    assert "Python" in exc.value.title


def test_corrupt_db_fails_before_servers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_launcher()
    python = Path(sys.executable)
    assert python.is_file()
    (tmp_path / "web" / ".next").mkdir(parents=True)
    (tmp_path / "web" / ".next" / "BUILD_ID").write_text("test", encoding="utf-8")
    monkeypatch.setattr(mod, "WEB_DIR", tmp_path / "web")
    monkeypatch.setattr(mod, "ICON_ICO", tmp_path / "docly-icon.ico")
    (tmp_path / "docly-icon.ico").write_bytes(b"0" * 16)
    monkeypatch.setattr(mod, "_venv_python", lambda: python)
    monkeypatch.setenv("DOCLY_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DOCLY_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("DOCLY_NO_BROWSER", "1")
    data = tmp_path / "data"
    data.mkdir()
    (data / "docly.db").write_bytes(b"not-a-database")
    launcher = mod.DoclyLauncher()
    environment = os.environ.copy()
    try:
        with pytest.raises(mod.LaunchError) as exc:
            launcher.run()
        assert "баз" in exc.value.title.lower()
    finally:
        os.environ.clear()
        os.environ.update(environment)
