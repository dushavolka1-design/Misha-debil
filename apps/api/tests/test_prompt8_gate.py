from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.auth_consent import AuthConsentStore, seed_demo_legal

ROOT = Path(__file__).resolve().parents[3]
LEGAL = ROOT / "legal"


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        store: AuthConsentStore = c.app.state.auth_store
        if not store.legal:
            seed_demo_legal(store, str(LEGAL))
        yield c


def test_prompt8_catalog_has_eight_cards(client: TestClient) -> None:
    res = client.get("/forms")
    assert res.status_code == 200
    forms = res.json()
    assert len(forms) == 8, "Каталог не должен быть пустым"


def test_prompt8_published_government_forms_require_official_raw(client: TestClient) -> None:
    forms = client.get("/forms").json()
    published_gov = [f for f in forms if f["status"] == "published" and f["form_kind"] == "government_form"]
    for form in published_gov:
        assert form.get("has_raw") and form.get("content_sha256"), (
            f"Published gov form {form['slug']} missing official raw/hash"
        )


def test_prompt8_demo_mode_fixture_forbidden_when_demo_off(client: TestClient) -> None:
    settings = client.app.state  # type: ignore[attr-defined]
    _ = settings
    from app.settings import get_settings

    if get_settings().demo_mode:
        pytest.skip("DEMO_MODE=true — fixture_id allowed in demo")
    res = client.post(
        "/analysis/runs",
        json={"document_id": "00000000-0000-4000-8000-000000000099", "fixture_id": "digital_pdf"},
    )
    assert res.status_code in {401, 403, 404, 422}
    if res.status_code == 403:
        assert res.json()["detail"]["code"] == "fixture_forbidden"
