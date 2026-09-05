"""Legal package fixtures for acceptance / hash proofs."""

from __future__ import annotations

from pathlib import Path

LEGAL_ROOT = Path(__file__).resolve().parents[2] / "legal"

FIXTURE_CONSENT_IDS = [
    "offer",
    "terms_of_use",
    "privacy_policy",
    "personal_data_processing",
    "special_categories.medical",
    "cookies_notice",
    "marketing",
    "payment_recurring",
]


def load_canonical(consent_id: str, version: str = "2026.08.11.2", locale: str = "ru-RU") -> str:
    folder = "policies" if consent_id == "privacy_policy" else "consents"
    path = LEGAL_ROOT / folder / consent_id / f"{version}.{locale}.md"
    return path.read_text(encoding="utf-8")
