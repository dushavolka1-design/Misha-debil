from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

# Must run before app imports
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_FAKE_PROVIDERS", "true")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://dar_local:dar_local_password_change_me@localhost:5432/dar_local",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SESSION_SECRET", "test_session_secret_not_for_production_use")
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "dar_minio_access")
os.environ.setdefault("S3_SECRET_KEY", "dar_minio_secret_change_me")
os.environ.setdefault("S3_BUCKET_ORIGINALS", "dar-originals")
os.environ.setdefault("S3_BUCKET_DERIVED", "dar-derived")
os.environ.setdefault("S3_BUCKET_REPORTS", "dar-reports")
os.environ.setdefault("S3_BUCKET_QUARANTINE", "dar-quarantine")
os.environ.setdefault("OBJECT_STORAGE_PROVIDER", "fake_object_storage")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("OCR_PROVIDER", "fake_ocr")
os.environ.setdefault("LLM_PROVIDER", "fake_llm")
os.environ.setdefault("MALWARE_SCANNER_PROVIDER", "fake_malware")
os.environ.setdefault("PAYMENT_PROVIDER", "fake_payment")
os.environ.setdefault("EMAIL_PROVIDER", "fake_email")
os.environ.setdefault("KMS_PROVIDER", "fake_kms")


def _clear_runtime_caches() -> None:
    from app.db import get_engine, get_session_factory
    from app.persistence.sync_db import get_sync_engine, get_sync_session_factory
    from app.settings import get_settings

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_sync_engine.cache_clear()
    get_sync_session_factory.cache_clear()


@pytest.fixture(autouse=True)
def _restore_test_env_after_desktop() -> Iterator[None]:
    # Desktop helpers mutate process-wide settings. Restore the complete input
    # environment, including provider and queue choices, even after a failure.
    previous = dict(os.environ)
    _clear_runtime_caches()
    try:
        yield
    finally:
        for key in set(os.environ) - previous.keys():
            del os.environ[key]
        os.environ.update(previous)
        _clear_runtime_caches()


@pytest.fixture(autouse=True)
def _isolate_rate_limit_state() -> Iterator[None]:
    from app.security.rate_limit import rate_limiter

    # Every test gets the real limiter with unchanged thresholds. Requests within
    # the same test still accumulate, so rate-limit regressions remain effective.
    with rate_limiter._lock:
        rate_limiter._events.clear()
    try:
        yield
    finally:
        with rate_limiter._lock:
            rate_limiter._events.clear()
