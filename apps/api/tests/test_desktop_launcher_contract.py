from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WIN = ROOT / "scripts" / "windows"


def _read(name: str) -> str:
    return (WIN / name).read_text(encoding="utf-8", errors="replace")


def test_launcher_scripts_exist() -> None:
    assert (WIN / "docly_launcher.py").is_file()
    assert (WIN / "doctor.ps1").is_file()
    assert (WIN / "setup-desktop.ps1").is_file()
    assert (WIN / "assets" / "docly-icon.ico").is_file()
    assert (WIN / "assets" / "docly-logo.png").is_file()


def test_desktop_launcher_does_not_download_postgres_or_redis() -> None:
    for name in ("start-dar.ps1", "docly_launcher.py", "setup-desktop.ps1", "doctor.ps1"):
        text = _read(name)
        assert "setup-portable-db" not in text
        assert "enterprisedb.com" not in text
        assert "Ensure-BundledDatabase" not in text


def test_desktop_launcher_does_not_use_next_dev() -> None:
    text = _read("docly_launcher.py") + _read("start-dar.ps1")
    assert "next dev" not in text
    assert '", "dev",' not in text
    launcher = _read("docly_launcher.py")
    assert '"start"' in launcher
    assert "next_js" in launcher


def test_desktop_launcher_does_not_kill_foreign_ports() -> None:
    text = _read("docly_launcher.py") + _read("start-dar.ps1")
    assert "Stop-PortListener" not in text
    assert "Stop-Process -Id $conn.OwningProcess" not in text
    assert "taskkill" not in _read("docly_launcher.py").split("def stop_instance")[0]


def test_shortcut_installer_is_visible_and_uses_existing_icon() -> None:
    vbs = _read("install-shortcuts.vbs")
    assert "WindowStyle Hidden" not in vbs
    assert "docly-icon.ico" in vbs
    assert "docly_launcher.py" in vbs
    silent = _read("start-dar-silent.vbs")
    assert "Hidden" not in silent.replace("WindowStyle", "")
    assert "WindowStyle Hidden" not in silent


def test_splash_has_russian_stages_and_actions() -> None:
    text = _read("docly_launcher.py")
    for needle in (
        "Проверка файлов",
        "Запуск хранилища",
        "Запуск сервиса",
        "Открытие приложения",
        "Показать подробности",
        "Повторить",
        "Скопировать диагностику",
    ):
        assert needle in text


def test_doctor_does_not_silently_migrate() -> None:
    text = _read("doctor.ps1")
    assert "migrate_sqlite" not in text
    assert "setup-portable-db" not in text
