"""Prompt 2: form catalog must restore FormRecord after persistence restart."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.db import get_engine, get_session_factory
from app.desktop_boot import apply_desktop_env, migrate_sqlite
from app.persistence.sync_db import get_sync_engine, get_sync_session_factory
from app.services.forms.catalog import FormCatalogService, FormRecord
from app.services.forms.catalog_seed import seed_prompt6_catalog
from app.services.sources.registry import SourceRegistry
from app.settings import get_settings


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_sync_engine.cache_clear()
    get_sync_session_factory.cache_clear()


def _desktop_app(data_dir: Path):
    apply_desktop_env(data_dir=data_dir, instance_token="catalog-token")
    migrate_sqlite(data_dir)
    _clear_caches()
    from app.main import create_app

    return create_app()


def test_dict_payload_is_isolated_not_500() -> None:
    """One corrupted dict must not crash list_forms or wipe the catalog."""
    sources = SourceRegistry()
    catalog = FormCatalogService(sources)
    seed_prompt6_catalog(catalog)
    good_ids = set(catalog.forms.keys())
    from uuid import uuid4

    catalog.forms[uuid4()] = {"slug": "broken", "title": "x"}  # type: ignore[assignment]
    cards = catalog.list_forms()
    assert len(cards) == 8
    assert all(isinstance(rec, FormRecord) for rec in cards)
    assert {rec.id for rec in cards} == good_ids
    assert catalog.quarantine
    assert catalog.quarantine[0]["code"] == "catalog_record_invalid"


def test_eight_form_records_survive_app_restart(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    app1 = _desktop_app(data)
    with TestClient(app1) as client:
        first = client.get("/forms")
        assert first.status_code == 200, first.text
        cards = first.json()
        assert isinstance(cards, list)
        assert len(cards) == 8
        ids = {c["id"] for c in cards}
        assert all(c.get("status") for c in cards)
        assert all(c.get("slug") for c in cards)
    _clear_caches()

    app2 = _desktop_app(data)
    with TestClient(app2) as client:
        second = client.get("/forms")
        assert second.status_code == 200, second.text
        cards2 = second.json()
        assert len(cards2) == 8
        assert {c["id"] for c in cards2} == ids
        for card in cards2:
            assert isinstance(card["status"], str)
            assert card["title"]
        ready = client.get("/ready")
        assert ready.status_code == 200, ready.text
        body = ready.json()
        assert body["status"] == "ready"
        assert body["checks"].get("catalog") is True
        catalog = client.app.state.form_catalog
        assert all(isinstance(rec, FormRecord) for rec in catalog.forms.values())
    _clear_caches()


def test_apply_invariants_keeps_catalog_typed() -> None:
    from uuid import uuid4

    sources = SourceRegistry()
    catalog = FormCatalogService(sources)
    seed_prompt6_catalog(catalog)
    rec = next(iter(catalog.iter_records()))
    rec.fill_version_id = uuid4()
    rec.fill_ready = True
    catalog.by_slug["ghost"] = uuid4()
    catalog.apply_invariants(fill_version_ids=set(), snapshot_ids=set())
    assert rec.fill_version_id is None
    assert rec.fill_ready is False
    assert "ghost" not in catalog.by_slug
    assert all(isinstance(item, FormRecord) for item in catalog.forms.values())
    gov = next(r for r in catalog.iter_records() if r.form_kind == "government_form")
    catalog.update_fields(gov.id, status="published", source_snapshot_id=None)
    catalog.apply_invariants(fill_version_ids=set(), snapshot_ids=set())
    assert catalog.get(gov.id).status == "needs_review"


def test_legacy_blob_dicts_repaired_to_form_records(tmp_path: Path) -> None:
    from uuid import uuid4

    from app.models import AppStateBlob
    from app.persistence.sync_db import sync_session
    from app.services.forms.catalog_seed import PROMPT6_CARDS

    data = tmp_path / "data"
    data.mkdir()
    apply_desktop_env(data_dir=data, instance_token="blob-token")
    migrate_sqlite(data)
    _clear_caches()
    payload: dict = {}
    for spec in PROMPT6_CARDS:
        uid = str(uuid4())
        payload[uid] = {
            **spec,
            "id": uid,
            "authority": spec["organ"],
            "source_snapshot_id": None,
            "content_sha256": None,
            "raw_size": 0,
            "act_number": None,
            "act_date": None,
            "act_title": None,
            "valid_from": None,
            "valid_to": None,
            "reviewed_at": None,
            "reviewer": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "edition_note": "blob",
            "fill_version_id": None,
        }
    payload[str(uuid4())] = {"title": "broken-without-slug"}
    with sync_session() as sess:
        sess.add(AppStateBlob(namespace="forms", blob_key="forms", value_json=payload))
        sess.commit()

    app = _desktop_app(data)
    with TestClient(app) as client:
        res = client.get("/forms")
        assert res.status_code == 200, res.text
        cards = res.json()
        assert len(cards) == 8
        assert all(c.get("title") and c.get("slug") for c in cards)
        diag = client.get("/forms/diagnostics")
        assert diag.status_code == 200
        isolated = diag.json()["isolated"]
        assert any(item["code"] == "catalog_record_invalid" for item in isolated)
        catalog = client.app.state.form_catalog
        assert all(isinstance(rec, FormRecord) for rec in catalog.forms.values())
    _clear_caches()
