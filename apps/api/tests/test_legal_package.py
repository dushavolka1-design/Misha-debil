from __future__ import annotations

from pathlib import Path

import pytest
from dar.legal_gate import assert_legal_production_ready, validate_legal_package
from dar.settings_base import BaseAppSettings

LEGAL = Path(__file__).resolve().parents[3] / "legal"


def test_legal_package_draft_ok_for_non_production() -> None:
    report = validate_legal_package(LEGAL, for_production=False)
    assert report.ok, report.errors
    assert report.warnings  # placeholders expected in drafts
    assert report.manifest is not None
    ids = {d["consent_id"] for d in report.manifest["documents"]}
    for required in (
        "offer",
        "terms_of_use",
        "privacy_policy",
        "personal_data_processing",
        "special_categories.medical",
        "cookies_notice",
        "marketing",
        "payment_recurring",
    ):
        assert required in ids


def test_legal_package_production_fails_on_draft_placeholders() -> None:
    report = validate_legal_package(LEGAL, for_production=True)
    assert report.ok is False
    assert any("approved" in e or "placeholder" in e for e in report.errors)
    with pytest.raises(RuntimeError, match="Legal package"):
        assert_legal_production_ready(LEGAL)


def test_documents_are_separate_files() -> None:
    # PD consent must not live inside offer/terms files
    offer = (LEGAL / "consents/offer/2026.08.11.2.ru-RU.md").read_text(encoding="utf-8")
    terms = (LEGAL / "consents/terms_of_use/2026.08.28.1.ru-RU.md").read_text(encoding="utf-8")
    pd = (LEGAL / "consents/personal_data_processing/2026.08.11.2.ru-RU.md").read_text(encoding="utf-8")
    assert "consent_id: personal_data_processing" in pd
    assert "Не объединяется с офертой" in pd or "не объединяется" in pd.lower()
    assert "consent_id: offer" in offer
    assert "consent_id: terms_of_use" in terms
    assert "не являются" in terms.lower() and "официальными бланками мвд" in terms.lower()
    assert "bundled" in pd.lower() or "Отдельное согласие" in pd


def test_special_consent_flags_mechanism_review() -> None:
    text = (LEGAL / "consents/special_categories.medical/2026.08.11.2.ru-RU.md").read_text(encoding="utf-8")
    assert "FINAL_CONSENT_MECHANISM_NEEDS_LEGAL_REVIEW" in text
    assert "Не запрашивается при регистрации" in text


def test_offer_has_cancel_and_consumer_rights() -> None:
    text = (LEGAL / "consents/offer/2026.08.11.2.ru-RU.md").read_text(encoding="utf-8")
    assert "Отмена подписки" in text or "отменить" in text.lower()
    assert "без обращения в поддержку" in text.lower() or "без" in text and "поддержк" in text
    assert "обязательные права потребителя" in text.lower() or "прав потребителя" in text


def test_production_settings_require_legal_root(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {
        "APP_ENV": "production",
        "ALLOW_FAKE_PROVIDERS": "false",
        "DATABASE_URL": "postgresql+psycopg://prod_user:prod_strong_password@db:5432/dar",
        "REDIS_URL": "redis://redis:6379/0",
        "SESSION_SECRET": "production_session_secret_value_32b",
        "OCR_PROVIDER": "vendor_ocr",
        "LLM_PROVIDER": "vendor_llm",
        "OBJECT_STORAGE_PROVIDER": "s3",
        "MALWARE_SCANNER_PROVIDER": "vendor_malware",
        "PAYMENT_PROVIDER": "vendor_payment",
        "EMAIL_PROVIDER": "vendor_email",
        "KMS_PROVIDER": "vendor_kms",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("LEGAL_ROOT", raising=False)
    settings = BaseAppSettings()  # type: ignore[call-arg]
    with pytest.raises(RuntimeError, match="LEGAL_ROOT"):
        settings.validate_runtime_safety()


def test_production_settings_fail_on_draft_legal(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {
        "APP_ENV": "production",
        "ALLOW_FAKE_PROVIDERS": "false",
        "DATABASE_URL": "postgresql+psycopg://prod_user:prod_strong_password@db:5432/dar",
        "REDIS_URL": "redis://redis:6379/0",
        "SESSION_SECRET": "production_session_secret_value_32b",
        "OCR_PROVIDER": "vendor_ocr",
        "LLM_PROVIDER": "vendor_llm",
        "OBJECT_STORAGE_PROVIDER": "s3",
        "MALWARE_SCANNER_PROVIDER": "vendor_malware",
        "PAYMENT_PROVIDER": "vendor_payment",
        "EMAIL_PROVIDER": "vendor_email",
        "KMS_PROVIDER": "vendor_kms",
        "LEGAL_ROOT": str(LEGAL),
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    settings = BaseAppSettings()  # type: ignore[call-arg]
    with pytest.raises(RuntimeError, match="Legal package|approved|placeholder"):
        settings.validate_runtime_safety()
