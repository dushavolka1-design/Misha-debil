from __future__ import annotations

from functools import lru_cache

from dar.settings_base import BaseAppSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict


class Settings(BaseAppSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_public_base_url: str = Field(default="http://localhost:8000", alias="API_PUBLIC_BASE_URL")
    web_origin: str = Field(default="http://localhost:3000", alias="WEB_ORIGIN")
    legal_root: str | None = Field(default=None, alias="LEGAL_ROOT")

    s3_endpoint_url: str = Field(default="http://127.0.0.1:9000", alias="S3_ENDPOINT_URL")
    s3_access_key: str = Field(default="dar_minio_access", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="dar_minio_secret_change_me", alias="S3_SECRET_KEY")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_bucket_originals: str = Field(default="dar-originals", alias="S3_BUCKET_ORIGINALS")
    s3_bucket_derived: str = Field(default="dar-derived", alias="S3_BUCKET_DERIVED")
    s3_bucket_reports: str = Field(default="dar-reports", alias="S3_BUCKET_REPORTS")
    s3_bucket_quarantine: str = Field(default="dar-quarantine", alias="S3_BUCKET_QUARANTINE")

    retention_originals_days: int = Field(default=30, alias="RETENTION_ORIGINALS_DAYS")
    retention_derived_days: int = Field(default=60, alias="RETENTION_DERIVED_DAYS")
    retention_reports_days: int = Field(default=90, alias="RETENTION_REPORTS_DAYS")
    retention_audit_days: int = Field(default=365, alias="RETENTION_AUDIT_DAYS")
    retention_medical_originals_days: int = Field(default=7, alias="RETENTION_MEDICAL_ORIGINALS_DAYS")
    retention_medical_derived_days: int = Field(default=7, alias="RETENTION_MEDICAL_DERIVED_DAYS")

    queue_name: str = Field(default="dar-jobs", alias="QUEUE_NAME")
    upload_presign_ttl_seconds: int = Field(default=600, alias="UPLOAD_PRESIGN_TTL_SECONDS")
    sandbox_cpu_seconds: float = Field(default=5.0, alias="SANDBOX_CPU_SECONDS")
    sandbox_memory_mb: int = Field(default=256, alias="SANDBOX_MEMORY_MB")

    # Billing: production requires approved offer version matching legal package
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
    max_analysis_pages: int = Field(default=50, alias="MAX_ANALYSIS_PAGES")
    approved_offer_version: str | None = Field(default=None, alias="APPROVED_OFFER_VERSION")


@lru_cache
def get_settings() -> Settings:
    import os
    from pathlib import Path

    # Resolve repo legal/ for production gate (Dockerfile should COPY legal → /app/legal)
    if not os.environ.get("LEGAL_ROOT"):
        candidate = Path(__file__).resolve().parents[3] / "legal"
        if candidate.is_dir():
            os.environ["LEGAL_ROOT"] = str(candidate)
    settings = Settings()  # type: ignore[call-arg]
    settings.validate_runtime_safety()
    return settings
