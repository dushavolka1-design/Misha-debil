"""Prompt 2: form catalog and fill API contracts survive process restart."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from docly_auth_test_support import assert_desktop_email_is_verified
from fastapi.testclient import TestClient

from app.db import get_engine, get_session_factory
from app.desktop_boot import apply_desktop_env, migrate_sqlite
from app.persistence.sync_db import get_sync_engine, get_sync_session_factory
from app.services.auth_consent import REQUIRED_AT_REGISTRATION
from app.services.forms.catalog import FormRecord
from app.settings import get_settings

ANSWERS = {"visit_date": "2026-01-15", "questions": "Какие анализы нужны"}
USER_EMAIL = "filluser@example.com"
USER_PASSWORD = "longpassword1"


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_sync_engine.cache_clear()
    get_sync_session_factory.cache_clear()


def _desktop_app(data_dir: Path):
    apply_desktop_env(data_dir=data_dir, instance_token="contract-token")
    migrate_sqlite(data_dir)
    _clear_caches()
    from app.main import create_app

    return create_app()


def _session(data_dir: Path) -> TestClient:
    return TestClient(_desktop_app(data_dir))


def _login(client: TestClient) -> None:
    login = client.post("/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD})
    if login.status_code == 200:
        return
    store = client.app.state.auth_store
    accepts = []
    for cid in REQUIRED_AT_REGISTRATION:
        doc = store.active_legal(cid)
        assert doc
        accepts.append(
            {
                "consent_id": doc.consent_id,
                "consent_version": doc.consent_version,
                "content_hash": doc.content_hash,
            },
        )
    registered = client.post(
        "/auth/register",
        json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD,
            "display_name": "Иван Тестов",
            "locale": "ru-RU",
            "accepts": accepts,
        },
    )
    assert registered.status_code == 200, registered.text
    token = registered.json().get("verification_token_dev")
    assert token
    assert_desktop_email_is_verified(client, token)
    login = client.post("/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD})
    assert login.status_code == 200, login.text


def test_form_fill_contract_with_restart_between_steps(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    catalog_id: str | None = None
    version_id: str | None = None
    generated_id: str | None = None

    with _session(data) as client:
        forms = client.get("/forms")
        assert forms.status_code == 200, forms.text
        cards = forms.json()
        assert len(cards) == 8
        arrival = next(c for c in cards if c["slug"] == "mvd.arrival_notice.app4")
        assert arrival["fill_ready"] is False
        medical = next(c for c in cards if c["slug"] == "medical.visit.memo")
        assert medical["fill_ready"] is True
        catalog_id = medical["id"]
        assert all(isinstance(c["id"], str) and c["title"] for c in cards)
    _clear_caches()

    with _session(data) as client:
        one = client.get(f"/forms/{catalog_id}")
        assert one.status_code == 200, one.text
        body = one.json()
        assert body["id"] == catalog_id
        assert body["slug"] == "medical.visit.memo"
        catalog = client.app.state.form_catalog
        assert isinstance(catalog.get(UUID(catalog_id)), FormRecord)
    _clear_caches()

    with _session(data) as client:
        pkg = client.get(f"/forms/fill/by-catalog/{catalog_id}")
        assert pkg.status_code == 200, pkg.text
        payload = pkg.json()
        assert payload["available"] is True
        version_id = payload["version"]["id"]
        assert payload["catalog"]["id"] == catalog_id
        assert payload["catalog"]["form_kind"] == "medical_memo"
        arrival_id = next(c["id"] for c in client.get("/forms").json() if c["slug"] == "mvd.arrival_notice.app4")
        arrival_pkg = client.get(f"/forms/fill/by-catalog/{arrival_id}")
        assert arrival_pkg.status_code == 200
        assert arrival_pkg.json()["available"] is False
        assert arrival_pkg.json().get("checklist")
    _clear_caches()

    with _session(data) as client:
        preview = client.post(
            "/forms/fill/preview",
            json={"form_version_id": version_id, "answers": ANSWERS},
        )
        assert preview.status_code == 200, preview.text
        assert preview.json()["ok"] is True
    _clear_caches()

    with _session(data) as client:
        _login(client)
        draft = client.put(
            "/forms/fill/drafts",
            json={"catalog_form_id": catalog_id, "answers": ANSWERS},
        )
        assert draft.status_code == 200, draft.text
        gen = client.post(
            "/forms/fill/generate",
            json={"form_version_id": version_id, "answers": ANSWERS, "catalog_form_id": catalog_id},
        )
        assert gen.status_code == 200, gen.text
        generated_id = gen.json()["generated_id"]
        assert generated_id
    _clear_caches()

    with _session(data) as client:
        _login(client)
        saved = client.get(f"/forms/fill/drafts?catalog_form_id={catalog_id}")
        assert saved.status_code == 200, saved.text
        assert saved.json()["draft"]
        assert saved.json()["draft"]["answers"]["visit_date"] == ANSWERS["visit_date"]
        pdf = client.get(f"/forms/fill/generated/{generated_id}/pdf")
        assert pdf.status_code == 200, pdf.text
        assert pdf.content.startswith(b"%PDF")
        assert "attachment" in (pdf.headers.get("content-disposition") or "").lower()
        ready = client.get("/ready")
        assert ready.status_code == 200, ready.text
        assert ready.json()["checks"]["catalog"] is True
        assert ready.json()["checks"]["font"] is True
        caps = client.get("/capabilities")
        assert caps.status_code == 200, caps.text
        body = caps.json()
        assert body["font_ready"] is True
        assert body["catalog_ready"] is True
        assert body["official_templates_count"] == 0
        assert body["generation_ready"] is True
        catalog = client.app.state.form_catalog
        fill = client.app.state.form_fill
        assert all(isinstance(rec, FormRecord) for rec in catalog.forms.values())
        assert all(not isinstance(v, dict) for v in fill.versions.values())
        assert all(not isinstance(v, dict) for v in fill.drafts.values())
        assert all(not isinstance(v, dict) for v in fill.generated.values())
    _clear_caches()
