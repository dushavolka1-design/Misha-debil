"""API-facing legal package helpers — re-export gate + seed map."""

from __future__ import annotations

from dar.legal_gate import (
    DEFAULT_PLACEHOLDERS,
    LegalPackageReport,
    assert_legal_production_ready,
    load_manifest,
    validate_legal_package,
)

LEGAL_DOC_SEED = (
    ("terms_of_use", "2026.08.28.1", "ru-RU", "consents"),
    ("offer", "2026.08.11.2", "ru-RU", "consents"),
    ("personal_data_processing", "2026.08.11.2", "ru-RU", "consents"),
    ("marketing", "2026.08.11.2", "ru-RU", "consents"),
    ("special_categories.medical", "2026.08.11.2", "ru-RU", "consents"),
    ("cookies_notice", "2026.08.11.2", "ru-RU", "consents"),
    ("payment_recurring", "2026.08.11.2", "ru-RU", "consents"),
    ("privacy_policy", "2026.08.11.2", "ru-RU", "policies"),
)


def assert_legal_package_for_env(legal_root: str, *, app_env: str) -> LegalPackageReport:
    report = validate_legal_package(legal_root, for_production=(app_env == "production"))
    if app_env == "production":
        report.raise_for_production()
    return report


__all__ = [
    "DEFAULT_PLACEHOLDERS",
    "LEGAL_DOC_SEED",
    "LegalPackageReport",
    "assert_legal_package_for_env",
    "assert_legal_production_ready",
    "load_manifest",
    "validate_legal_package",
]
