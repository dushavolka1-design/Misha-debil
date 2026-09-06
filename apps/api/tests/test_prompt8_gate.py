from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.auth_consent import REQUIRED_AT_REGISTRATION, AuthConsentStore, seed_demo_legal
from app.settings import get_settings

ROOT = Path(__file__).resolve().parents[3]
LEGAL = ROOT / "legal"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    # This suite must exercise the non-demo security boundary independently of
    # developer/CI defaults. Shared conftest restores the environment afterwards.
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()
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
    assert get_settings().demo_mode is False
    assert client.app.state.providers.settings.demo_mode is False
    store: AuthConsentStore = client.app.state.auth_store
    accepts = []
    for consent_id in REQUIRED_AT_REGISTRATION:
        document = store.active_legal(consent_id)
        assert document is not None
        accepts.append(
            {
                "consent_id": document.consent_id,
                "consent_version": document.consent_version,
                "content_hash": document.content_hash,
            },
        )
    credentials = {"email": "demo-boundary@example.com", "password": "longpassword1"}
    registered = client.post(
        "/auth/register",
        json={**credentials, "display_name": "Проверка Режима", "locale": "ru-RU", "accepts": accepts},
    )
    assert registered.status_code == 200, registered.text
    token = registered.json()["verification_token_dev"]
    verified = client.post("/auth/verify-email", json={"token": token})
    assert verified.status_code == 200, verified.text
    logged_in = client.post("/auth/login", json=credentials)
    assert logged_in.status_code == 200, logged_in.text
    assert client.get("/auth/me").status_code == 200

    res = client.post(
        "/analysis/runs",
        json={"document_id": "00000000-0000-4000-8000-000000000099", "fixture_id": "digital_pdf"},
    )
    # 401/404/422 are not evidence of the demo gate. Require its exact contract
    # for an authenticated account, before any document lookup or job enqueue.
    assert res.status_code == 400, res.text
    assert res.json()["detail"]["code"] == "fixture_forbidden"
