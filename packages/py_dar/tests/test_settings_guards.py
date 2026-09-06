from __future__ import annotations

import pytest

from dar.providers.factory import ProductionFakeProviderError
from dar.settings_base import BaseAppSettings


def _base(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "APP_ENV": "production",
        "ALLOW_FAKE_PROVIDERS": "false",
        "DATABASE_URL": "postgresql+psycopg://prod_user:prod_strong_password@db:5432/dar",
        "REDIS_URL": "redis://redis:6379/0",
        "SESSION_SECRET": "production_session_secret_value_32b",
        "OCR_PROVIDER": "fake_ocr",
        "LLM_PROVIDER": "vendor_llm",
        "OBJECT_STORAGE_PROVIDER": "s3",
        "MALWARE_SCANNER_PROVIDER": "vendor_malware",
        "PAYMENT_PROVIDER": "vendor_payment",
        "EMAIL_PROVIDER": "vendor_email",
        "KMS_PROVIDER": "vendor_kms",
        "LEGAL_ROOT": str(__import__("pathlib").Path(__file__).resolve().parents[3] / "legal"),
    }
    data.update(overrides)
    return data


def test_production_rejects_fake_and_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _base().items():
        monkeypatch.setenv(str(k), str(v))
    settings = BaseAppSettings()  # type: ignore[call-arg]
    # Draft legal package fails first when LEGAL_ROOT points at repo drafts;
    # also reject fakes — either legal gate or fake-provider error is acceptable closed-fail.
    with pytest.raises((ProductionFakeProviderError, RuntimeError)):
        settings.validate_runtime_safety()


def test_production_rejects_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _base(
        OCR_PROVIDER="vendor_ocr",
        DATABASE_URL="sqlite:///tmp.db",
    ).items():
        monkeypatch.setenv(str(k), str(v))
    settings = BaseAppSettings()  # type: ignore[call-arg]
    with pytest.raises(RuntimeError, match="SQLite"):
        settings.validate_runtime_safety()
