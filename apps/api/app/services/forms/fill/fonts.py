"""Font resolution for form fill — bundled OFL font only; no system fallback."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

ASSETS = Path(__file__).resolve().parent / "assets"
MANIFEST = ASSETS / "font-manifest.json"

FONT_LICENSE_NOTE = (
    "Noto Sans Regular, SIL Open Font License 1.1. "
    "Pixel-perfect fill uses the bundled TTF only — see fill/assets/LICENSE."
)


@dataclass(frozen=True)
class FontStatus:
    ok: bool
    reason: str
    path: Path | None = None
    sha256: str | None = None
    license_ok: bool = False


def _load_manifest() -> dict:
    if not MANIFEST.is_file():
        return {}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def bundled_font_status() -> FontStatus:
    manifest = _load_manifest()
    filename = str(manifest.get("filename") or "NotoSans-Regular.ttf")
    bundled = ASSETS / filename
    expected = str(manifest.get("expected_sha256") or "").strip().lower()
    license_file = ASSETS / str(manifest.get("license_file") or "LICENSE")
    license_ok = license_file.is_file() and "SIL OPEN FONT LICENSE" in license_file.read_text(encoding="utf-8").upper()
    if not expected:
        return FontStatus(ok=False, reason="Не зафиксирован SHA-256 шрифта форм.", license_ok=license_ok)
    if not bundled.is_file():
        return FontStatus(
            ok=False,
            reason="В дистрибутиве нет файла шрифта Noto Sans для заполнения форм.",
            license_ok=license_ok,
        )
    actual = hashlib.sha256(bundled.read_bytes()).hexdigest().lower()
    if actual != expected:
        return FontStatus(
            ok=False,
            reason="Контрольная сумма шрифта форм не совпадает с зафиксированной.",
            path=bundled,
            sha256=actual,
            license_ok=license_ok,
        )
    if not license_ok:
        return FontStatus(
            ok=False,
            reason="Рядом со шрифтом нет текста лицензии SIL OFL.",
            path=bundled,
            sha256=actual,
            license_ok=False,
        )
    return FontStatus(ok=True, reason="", path=bundled, sha256=actual, license_ok=True)


def assert_bundled_font() -> Path:
    status = bundled_font_status()
    if not status.ok or status.path is None:
        raise FileNotFoundError(status.reason or "Bundled form font is not ready")
    return status.path


def resolve_allowed_font() -> Path:
    """Return the bundled OFL TTF. Never fall back to Arial or other system fonts."""
    return assert_bundled_font()


def font_hash(path: Path | None = None) -> str:
    p = path or resolve_allowed_font()
    return hashlib.sha256(p.read_bytes()).hexdigest()
