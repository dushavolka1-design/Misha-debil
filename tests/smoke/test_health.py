from __future__ import annotations

import os

# Ensure env before imports (pytest may load this path directly)
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
os.environ.setdefault("OBJECT_STORAGE_PROVIDER", "fake_object_storage")

from fastapi.testclient import TestClient

from app.deps import ProviderBundle, build_providers
from app.main import create_app
from app.routers import health
from app.settings import get_settings


def test_live_and_health_smoke() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    app = create_app()
    bundle = build_providers(settings)
    app.dependency_overrides[health.get_bundle] = lambda: bundle

    with TestClient(app) as client:
        live = client.get("/live")
        assert live.status_code == 200
        assert live.json()["status"] == "ok"

        health_resp = client.get("/health")
        assert health_resp.status_code == 200
        body = health_resp.json()
        assert body["status"] == "ok"
        assert "service" in body
        assert "password" not in health_resp.text.lower()
        assert "secret" not in health_resp.text.lower()
