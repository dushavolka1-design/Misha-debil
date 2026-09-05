from __future__ import annotations

import json

# Ensure local/test defaults for export without requiring live infra
import os
from pathlib import Path

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("ALLOW_FAKE_PROVIDERS", "true")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://dar_local:dar_local_password_change_me@localhost:5432/dar_local",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SESSION_SECRET", "local_session_secret_change_me_32chars_min")
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "dar_minio_access")
os.environ.setdefault("S3_SECRET_KEY", "dar_minio_secret_change_me")
os.environ.setdefault("S3_BUCKET_ORIGINALS", "dar-originals")
os.environ.setdefault("S3_BUCKET_DERIVED", "dar-derived")
os.environ.setdefault("S3_BUCKET_REPORTS", "dar-reports")
os.environ.setdefault("OBJECT_STORAGE_PROVIDER", "fake_object_storage")

from app.main import create_app  # noqa: E402


def main() -> None:
    app = create_app()
    schema = app.openapi()
    out = Path(__file__).resolve().parents[2] / "openapi.json"
    # Also write into packages/contracts source of truth path via monorepo root
    contracts = Path(__file__).resolve().parents[3] / "packages" / "contracts" / "openapi" / "openapi.json"
    contracts.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
    out.write_text(payload, encoding="utf-8")
    contracts.write_text(payload, encoding="utf-8")
    print(f"Wrote {contracts}")


if __name__ == "__main__":
    main()
