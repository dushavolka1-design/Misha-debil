from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="APP_ENV")
    app_name: str = Field(default="document-analyzer-rf", alias="APP_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    allow_fake_providers: bool = Field(default=False, alias="ALLOW_FAKE_PROVIDERS")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    session_secret: str = Field(alias="SESSION_SECRET")
    queue_backend: str = Field(default="redis", alias="QUEUE_BACKEND")
    data_dir: str | None = Field(default=None, alias="DOCLY_DATA_DIR")
    instance_token: str = Field(default="", alias="DOCLY_INSTANCE_TOKEN")
    docly_profile: str = Field(default="", alias="DOCLY_PROFILE")

    ocr_provider: str = Field(default="local_extract", alias="OCR_PROVIDER")
    llm_provider: str = Field(default="unavailable", alias="LLM_PROVIDER")
    object_storage_provider: str = Field(default="s3", alias="OBJECT_STORAGE_PROVIDER")
    malware_scanner_provider: str = Field(default="fake_malware", alias="MALWARE_SCANNER_PROVIDER")
    payment_provider: str = Field(default="fake_payment", alias="PAYMENT_PROVIDER")
    email_provider: str = Field(default="fake_email", alias="EMAIL_PROVIDER")
    kms_provider: str = Field(default="fake_kms", alias="KMS_PROVIDER")

    @field_validator("database_url")
    @classmethod
    def forbid_sqlite_in_production(cls, value: str, info: object) -> str:
        # validated further in model_validator after env known
        return value

    def validate_runtime_safety(self) -> None:
        from dar.providers.factory import assert_providers_allowed

        if self.app_env == "production":
            if "sqlite" in self.database_url.lower():
                raise RuntimeError("SQLite is forbidden in production")
            if getattr(self, "queue_backend", "redis") == "sqlite":
                raise RuntimeError("SQLite queue is forbidden in production")
            if self.session_secret.startswith("local_") or "change_me" in self.session_secret:
                raise RuntimeError("Default/local SESSION_SECRET is forbidden in production")
            if "change_me" in self.database_url:
                raise RuntimeError("Default database credentials are forbidden in production")
            if self.allow_fake_providers:
                raise RuntimeError("ALLOW_FAKE_PROVIDERS must be false in production")
            import os

            legal_root = os.environ.get("LEGAL_ROOT")
            if not legal_root:
                raise RuntimeError("LEGAL_ROOT must be set in production to validate legal package")
            from dar.legal_gate import assert_legal_production_ready

            assert_legal_production_ready(legal_root)

        assert_providers_allowed(
            app_env=self.app_env,
            allow_fake=self.allow_fake_providers
            and self.app_env in {"local", "test", "desktop", "development"},
            selected=[
                self.ocr_provider,
                self.llm_provider,
                self.object_storage_provider
                if self.object_storage_provider != "s3"
                else "s3",
                self.malware_scanner_provider,
                self.payment_provider,
                self.email_provider,
                self.kms_provider,
            ],
        )
