from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import get_engine, get_session_factory
from app.desktop_boot import apply_desktop_env, migrate_sqlite
from app.persistence.sync_db import get_sync_engine, get_sync_session_factory
from app.settings import get_settings


@pytest.fixture
def desktop_client(tmp_path: Path):
    apply_desktop_env(data_dir=tmp_path, instance_token="http-token")
    migrate_sqlite(tmp_path)
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_sync_engine.cache_clear()
    get_sync_session_factory.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_sync_engine.cache_clear()
    get_sync_session_factory.cache_clear()


def test_desktop_live_ready_instance(desktop_client: TestClient) -> None:
    live = desktop_client.get("/live")
    assert live.status_code == 200
    ready = desktop_client.get("/ready")
    assert ready.status_code == 200, ready.text
    body = ready.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] is True
    assert body["checks"]["queue"] is True
    assert body["checks"]["object_storage"] is True
    assert body["checks"]["catalog"] is True
    inst = desktop_client.get("/instance")
    assert inst.status_code == 200
    payload = inst.json()
    assert payload["product"] == "docly"
    assert payload["instance_token"] == "http-token"
    assert payload["profile"] == "desktop"
