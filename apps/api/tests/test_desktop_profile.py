from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import select

from app.desktop_boot import (
    apply_desktop_env,
    find_free_port,
    is_our_instance,
    migrate_sqlite,
    parse_instance_payload,
)
from app.models import JobQueueItem
from app.settings import Settings, get_settings


@pytest.fixture
def desktop_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    apply_desktop_env(data_dir=tmp_path, instance_token="test-token")
    get_settings.cache_clear()
    from app.db import get_engine, get_session_factory

    get_engine.cache_clear()
    get_session_factory.cache_clear()
    from app.persistence.sync_db import get_sync_engine, get_sync_session_factory

    get_sync_engine.cache_clear()
    get_sync_session_factory.cache_clear()
    yield tmp_path
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_sync_engine.cache_clear()
    get_sync_session_factory.cache_clear()
    monkeypatch.delenv("APP_ENV", raising=False)


def test_desktop_uses_sqlite_file_queue_not_postgres(desktop_dir: Path) -> None:
    settings = Settings()  # type: ignore[call-arg]
    settings.validate_runtime_safety()
    assert settings.app_env == "desktop"
    assert "sqlite" in settings.database_url.lower()
    assert "postgresql" not in settings.database_url.lower()
    assert settings.queue_backend == "sqlite"
    assert settings.object_storage_provider == "file_object_storage"
    assert str(desktop_dir) in settings.database_url.replace(
        "\\", "/"
    ) or desktop_dir.as_posix() in settings.database_url.replace("\\", "/")


def test_production_still_forbids_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///C:/tmp/docly.db")
    monkeypatch.setenv("ALLOW_FAKE_PROVIDERS", "false")
    monkeypatch.setenv("SESSION_SECRET", "production_session_secret_value_32b")
    from dar.settings_base import BaseAppSettings

    s = BaseAppSettings()  # type: ignore[call-arg]
    with pytest.raises(RuntimeError, match="SQLite"):
        s.validate_runtime_safety()


def test_sqlite_migrate_and_queue_roundtrip(desktop_dir: Path) -> None:
    from app.services.jobs.broker import SqliteJobBroker

    db_path = migrate_sqlite(desktop_dir)
    assert db_path.is_file()
    broker = SqliteJobBroker(db_path, queue_name="dar-jobs")
    import asyncio

    async def _run() -> None:
        assert await broker.ping()
        await broker.enqueue("dar-jobs", {"type": "scan", "document_id": "00000000-0000-0000-0000-000000000001"})
        payload = await broker.pop("dar-jobs", timeout=0.2)
        assert payload is not None
        assert payload["type"] == "scan"
        empty = await broker.pop("dar-jobs", timeout=0.2)
        assert empty is None
        await broker.aclose()

    asyncio.run(_run())
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with Session(engine) as session:
        rows = session.scalars(select(JobQueueItem)).all()
        assert len(rows) >= 1


def test_file_storage_persists_bytes(desktop_dir: Path) -> None:
    from app.adapters.file_storage import FileObjectStorage
    import asyncio

    storage = FileObjectStorage(root=desktop_dir / "objects")

    async def _run() -> None:
        assert await storage.head_bucket(bucket="dar-originals")
        stored = await storage.put_bytes(
            bucket="dar-originals",
            key="a/b.bin",
            data=b"hello-docly",
            content_type="application/octet-stream",
        )
        raw = await storage.get_bytes(bucket=stored.bucket, key=stored.key)
        assert raw == b"hello-docly"
        await storage.delete_object(bucket=stored.bucket, key=stored.key)

    asyncio.run(_run())
    leftover = list((desktop_dir / "objects").rglob("*"))
    assert not any(p.is_file() for p in leftover)


def test_instance_identity_rejects_foreign_listener() -> None:
    payload = parse_instance_payload('{"product":"other","instance_token":"x","pid":1}')
    assert not is_our_instance(payload, expected_token="test-token")
    ours = parse_instance_payload('{"product":"docly","instance_token":"test-token","pid":9}')
    assert is_our_instance(ours, expected_token="test-token")


def test_find_free_port_skips_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    busy = {8000, 8001}

    def fake_open(port: int) -> bool:
        return port in busy

    port = find_free_port(8000, is_open=fake_open, limit=10)
    assert port == 8002


def test_cyrillic_and_spaces_data_dir(tmp_path: Path) -> None:
    nested = tmp_path / "Мои данные" / "Docly App"
    nested.mkdir(parents=True)
    apply_desktop_env(data_dir=nested, instance_token="t")
    get_settings.cache_clear()
    path = migrate_sqlite(nested)
    assert path.is_file()
    get_settings.cache_clear()


def test_corrupt_sqlite_is_reported(tmp_path: Path) -> None:
    apply_desktop_env(data_dir=tmp_path, instance_token="t")
    db = tmp_path / "docly.db"
    db.write_bytes(b"this is not a sqlite database")
    with pytest.raises(RuntimeError, match="SQLite|sqlite"):
        migrate_sqlite(tmp_path)


def test_production_forbids_sqlite_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("QUEUE_BACKEND", "sqlite")
    monkeypatch.setenv("ALLOW_FAKE_PROVIDERS", "false")
    monkeypatch.setenv("SESSION_SECRET", "production_session_secret_value_32b")
    monkeypatch.setenv("LEGAL_ROOT", str(Path(__file__).resolve().parents[3] / "legal"))
    from dar.settings_base import BaseAppSettings

    s = BaseAppSettings()  # type: ignore[call-arg]
    with pytest.raises(RuntimeError, match="SQLite queue"):
        s.validate_runtime_safety()
