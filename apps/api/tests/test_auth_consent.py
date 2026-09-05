from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.security.crypto import canonical_sha256, hash_password, verify_password
from app.services.auth_consent import (
    ALWAYS_ALLOWED_ACTIONS,
    REQUIRED_AT_REGISTRATION,
    SPECIAL_MEDICAL,
    AcceptSpec,
    AppendOnlyViolation,
    AuthConsentError,
    AuthConsentService,
    AuthConsentStore,
    seed_demo_legal,
)


ROOT = Path(__file__).resolve().parents[3]
LEGAL = ROOT / "legal"


@pytest.fixture()
def store() -> AuthConsentStore:
    s = AuthConsentStore()
    seed_demo_legal(s, str(LEGAL))
    return s


@pytest.fixture()
def service(store: AuthConsentStore) -> AuthConsentService:
    return AuthConsentService(store)


@pytest.fixture()
def client(store: AuthConsentStore, tmp_path: Path):
    from app.db import get_engine, get_session_factory
    from app.desktop_boot import apply_desktop_env, migrate_sqlite
    from app.persistence.sync_db import get_sync_engine, get_sync_session_factory
    from app.settings import get_settings

    data = tmp_path / "auth-data"
    data.mkdir()
    apply_desktop_env(data_dir=data, instance_token="auth-consent-test")
    migrate_sqlite(data)
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_sync_engine.cache_clear()
    get_sync_session_factory.cache_clear()
    app = create_app()
    # Replace store seeded in lifespan — TestClient runs lifespan
    with TestClient(app) as c:
        c.app.state.auth_store = store
        # Re-seed into the replaced store if empty
        if not store.legal:
            seed_demo_legal(store, str(LEGAL))
        yield c


def _active_accepts(store: AuthConsentStore, include_marketing: bool = False) -> list[dict]:
    ids = list(REQUIRED_AT_REGISTRATION) + (["marketing"] if include_marketing else [])
    out = []
    for cid in ids:
        doc = store.active_legal(cid)
        assert doc is not None
        out.append(
            {
                "consent_id": doc.consent_id,
                "consent_version": doc.consent_version,
                "content_hash": doc.content_hash,
            },
        )
    return out


def test_password_argon2() -> None:
    h = hash_password("correct-horse-battery")
    assert verify_password(h, "correct-horse-battery")
    assert not verify_password(h, "wrong")


def test_canonical_hash_stable() -> None:
    assert canonical_sha256("a\r\n") == canonical_sha256("a\n")


def test_append_only_guard(store: AuthConsentStore) -> None:
    with pytest.raises(AppendOnlyViolation):
        store.update_consent_event(store.consent_events[0].id if store.consent_events else __import__("uuid").uuid4())
    with pytest.raises(AppendOnlyViolation):
        store.delete_consent_event(__import__("uuid").uuid4())


def test_published_immutable(store: AuthConsentStore) -> None:
    doc = store.active_legal("terms_of_use")
    assert doc is not None
    with pytest.raises(AuthConsentError):
        store.mutate_published(doc.id, canonical_text="hacked")


def test_seed_demo_legal_upgrades_terms_of_use() -> None:
    store = AuthConsentStore()
    old_path = LEGAL / "consents/terms_of_use/2026.08.11.2.ru-RU.md"
    text = old_path.read_text(encoding="utf-8")
    store.publish_legal(
        consent_id="terms_of_use",
        consent_version="2026.08.11.2",
        locale="ru-RU",
        canonical_text=text,
        body_path=str(old_path.as_posix()),
        reviewer_id="reviewer_demo_local_only",
    )
    assert store.active_legal("terms_of_use").consent_version == "2026.08.11.2"
    seed_demo_legal(store, str(LEGAL))
    active = store.active_legal("terms_of_use")
    assert active is not None
    assert active.consent_version == "2026.08.28.1"
    lowered = active.canonical_text.lower()
    assert "не являются" in lowered
    assert "официальными бланками мвд" in lowered
    seed_demo_legal(store, str(LEGAL))
    again = [d for d in store.legal.values() if d.consent_id == "terms_of_use" and d.consent_version == "2026.08.28.1"]
    assert len(again) == 1


def test_register_requires_separate_pd_consent(service: AuthConsentService, store: AuthConsentStore) -> None:
    accepts = []
    for cid in ("terms_of_use", "offer"):
        doc = store.active_legal(cid)
        assert doc
        accepts.append(AcceptSpec(doc.consent_id, doc.consent_version, doc.content_hash))
    with pytest.raises(AuthConsentError) as ei:
        service.register(
            email="a@example.com",
            password="longpassword1",
            display_name="Иван Тестов",
            accepts=accepts,
            locale="ru-RU",
            ip="127.0.0.1",
            user_agent="test",
            request_id="r1",
        )
    assert ei.value.code == "consents_required"


def test_register_rejects_medical_at_signup(service: AuthConsentService, store: AuthConsentStore) -> None:
    accepts = []
    for cid in (*REQUIRED_AT_REGISTRATION, SPECIAL_MEDICAL):
        doc = store.active_legal(cid)
        assert doc
        accepts.append(AcceptSpec(doc.consent_id, doc.consent_version, doc.content_hash))
    with pytest.raises(AuthConsentError) as ei:
        service.register(
            email="b@example.com",
            password="longpassword1",
            display_name="Иван Тестов",
            accepts=accepts,
            locale="ru-RU",
            ip=None,
            user_agent=None,
            request_id="r2",
        )
    assert ei.value.code == "medical_consent_forbidden_at_registration"


def test_register_marketing_optional(service: AuthConsentService, store: AuthConsentStore) -> None:
    accepts = []
    for cid in REQUIRED_AT_REGISTRATION:
        doc = store.active_legal(cid)
        assert doc
        accepts.append(AcceptSpec(doc.consent_id, doc.consent_version, doc.content_hash))
    user, token, _msg = service.register(
        email="c@example.com",
        password="longpassword1",
        display_name="Иван Тестов",
        accepts=accepts,
        locale="ru-RU",
        ip="1.1.1.1",
        user_agent="ua",
        request_id="r3",
    )
    assert token
    assert service.store.has_active_accept(user.id, "personal_data_processing")
    assert not service.store.has_active_accept(user.id, "marketing")


def test_proof_reproduces_exact_text(service: AuthConsentService, store: AuthConsentStore) -> None:
    accepts = []
    for cid in REQUIRED_AT_REGISTRATION:
        doc = store.active_legal(cid)
        assert doc
        accepts.append(AcceptSpec(doc.consent_id, doc.consent_version, doc.content_hash))
    user, _, _ = service.register(
        email="d@example.com",
        password="longpassword1",
        display_name="Иван Тестов",
        accepts=accepts,
        locale="ru-RU",
        ip=None,
        user_agent=None,
        request_id="r4",
    )
    event = next(e for e in store.consent_events if e.subject_user_id == user.id and e.consent_id == "offer")
    text = service.proof_text(event.id)
    assert canonical_sha256(text) == event.content_hash
    assert text == store.legal[event.legal_document_id].canonical_text


def test_delete_allowed_without_new_offer_reaccept(service: AuthConsentService, store: AuthConsentStore) -> None:
    accepts = []
    for cid in REQUIRED_AT_REGISTRATION:
        doc = store.active_legal(cid)
        assert doc
        accepts.append(AcceptSpec(doc.consent_id, doc.consent_version, doc.content_hash))
    user, _, _ = service.register(
        email="e@example.com",
        password="longpassword1",
        display_name="Иван Тестов",
        accepts=accepts,
        locale="ru-RU",
        ip=None,
        user_agent=None,
        request_id="r5",
    )
    old = store.active_legal("offer")
    assert old
    store.publish_legal(
        consent_id="offer",
        consent_version="2026.08.11.2",
        locale="ru-RU",
        canonical_text=old.canonical_text + "\nMaterial change.\n",
        body_path="legal/consents/offer/2026.08.11.2.ru-RU.md",
        reviewer_id="reviewer_demo",
        supersedes_id=old.id,
    )
    with pytest.raises(AuthConsentError) as ei:
        service.assert_feature_allowed(user, "product_use")
    assert ei.value.code == "consent_required"
    # export/delete still ok
    assert "delete_account" in ALWAYS_ALLOWED_ACTIONS
    service.request_deletion(user)
    assert user.status == "deletion_requested"


def test_api_register_bypass_without_checkboxes_fails(client: TestClient, store: AuthConsentStore) -> None:
    res = client.post(
        "/auth/register",
        json={"email": "bypass@example.com", "password": "longpassword1", "display_name": "Иван Тестов", "locale": "ru-RU", "accepts": []},
    )
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "consents_required"


def test_api_register_and_login_session_cookie(client: TestClient, store: AuthConsentStore) -> None:
    accepts = _active_accepts(store)
    res = client.post(
        "/auth/register",
        json={
            "email": "ok@example.com",
            "password": "longpassword1",
            "display_name": "Иван Тестов",
            "locale": "ru-RU",
            "accepts": accepts,
        },
    )
    assert res.status_code == 200
    token = res.json()["verification_token_dev"]
    assert token
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200
    login = client.post("/auth/login", json={"email": "ok@example.com", "password": "longpassword1"})
    assert login.status_code == 200
    assert "dar_session" in login.cookies
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "ok@example.com"


def test_medical_upload_gate_blocks(client: TestClient, store: AuthConsentStore) -> None:
    accepts = _active_accepts(store)
    client.post(
        "/auth/register",
        json={"email": "med@example.com", "password": "longpassword1", "display_name": "Иван Тестов", "locale": "ru-RU", "accepts": accepts},
    )
    # verify + login
    # find user token from last register response — re-register won't work; use service path via store
    # Login after manually verifying
    from app.security.crypto import hash_token, utcnow

    user_id = store.users_by_email["med@example.com"]
    store.users[user_id].email_verified_at = utcnow()
    store.users[user_id].status = "active"
    login = client.post("/auth/login", json={"email": "med@example.com", "password": "longpassword1"})
    assert login.status_code == 200
    gate = client.post("/privacy/upload-gate", json={"potentially_medical": True, "filename": "scan.pdf"})
    assert gate.status_code == 200
    body = gate.json()
    assert body["allowed"] is False
    assert body["code"] == "consent_required"
    assert any("medical" in m for m in body["missing"])


def test_no_prechecked_boxes_in_openapi_semantics(store: AuthConsentStore) -> None:
    # Spec guard: marketing is optional and must not be in REQUIRED
    assert "marketing" not in REQUIRED_AT_REGISTRATION
    assert "personal_data_processing" in REQUIRED_AT_REGISTRATION
    assert "terms_of_use" in REQUIRED_AT_REGISTRATION
    assert "offer" in REQUIRED_AT_REGISTRATION


def test_register_rejects_weak_password_and_empty_name(service: AuthConsentService, store: AuthConsentStore) -> None:
    accepts = []
    for cid in REQUIRED_AT_REGISTRATION:
        doc = store.active_legal(cid)
        assert doc
        accepts.append(AcceptSpec(doc.consent_id, doc.consent_version, doc.content_hash))
    with pytest.raises(AuthConsentError) as ei:
        service.register(
            email="weak@example.com",
            password="abcdefghij",
            display_name="Иван Тестов",
            accepts=accepts,
            locale="ru-RU",
            ip=None,
            user_agent=None,
            request_id="weak",
        )
    assert ei.value.code == "weak_password"
    with pytest.raises(AuthConsentError) as ei2:
        service.register(
            email="noname@example.com",
            password="longpassword1",
            display_name="http://evil.example",
            accepts=accepts,
            locale="ru-RU",
            ip=None,
            user_agent=None,
            request_id="name",
        )
    assert ei2.value.code == "invalid_display_name"


def test_login_unverified_blocked_when_required(service: AuthConsentService, store: AuthConsentStore) -> None:
    accepts = []
    for cid in REQUIRED_AT_REGISTRATION:
        doc = store.active_legal(cid)
        assert doc
        accepts.append(AcceptSpec(doc.consent_id, doc.consent_version, doc.content_hash))
    user, token, _ = service.register(
        email="pending@example.com",
        password="longpassword1",
        display_name="Иван Ожидает",
        accepts=accepts,
        locale="ru-RU",
        ip=None,
        user_agent=None,
        request_id="pending",
    )
    assert token
    assert user.status == "pending_verification"
    blocked = service.login(
        email="pending@example.com",
        password="longpassword1",
        ip=None,
        user_agent=None,
        require_verified=True,
    )
    assert blocked is None
    allowed = service.login(
        username="Иван Ожидает",
        password="longpassword1",
        ip=None,
        user_agent=None,
        require_verified=False,
    )
    assert allowed is not None


def test_login_by_username_after_register(client: TestClient, store: AuthConsentStore) -> None:
    accepts = _active_accepts(store)
    res = client.post(
        "/auth/register",
        json={
            "email": "named@example.com",
            "password": "longpassword1",
            "display_name": "Мария Вход",
            "locale": "ru-RU",
            "accepts": accepts,
        },
    )
    assert res.status_code == 200, res.text
    login = client.post("/auth/login", json={"username": "мария вход", "password": "longpassword1"})
    assert login.status_code == 200, login.text
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["display_name"] == "Мария Вход"
    assert client.post("/auth/login", json={"email": "named@example.com", "password": "longpassword1"}).status_code == 200


def test_profile_name_and_avatar_roundtrip(client: TestClient, store: AuthConsentStore) -> None:
    import base64
    from io import BytesIO

    from PIL import Image

    accepts = _active_accepts(store)
    res = client.post(
        "/auth/register",
        json={
            "email": "avatar@example.com",
            "password": "longpassword1",
            "display_name": "Мария Петрова",
            "locale": "ru-RU",
            "accepts": accepts,
        },
    )
    assert res.status_code == 200
    token = res.json()["verification_token_dev"]
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200
    assert client.post("/auth/login", json={"email": "avatar@example.com", "password": "longpassword1"}).status_code == 200
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["display_name"] == "Мария Петрова"
    assert me.json()["has_avatar"] is False
    buf = BytesIO()
    Image.new("RGB", (40, 40), (12, 90, 200)).save(buf, format="PNG")
    data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    patched = client.patch("/auth/profile", json={"display_name": "Мария П", "avatar_data_url": data_url})
    assert patched.status_code == 200, patched.text
    assert patched.json()["display_name"] == "Мария П"
    assert patched.json()["has_avatar"] is True
    avatar = client.get("/auth/me/avatar")
    assert avatar.status_code == 200
    assert avatar.headers["content-type"].startswith("image/jpeg")
    assert avatar.content[:2] == b"\xff\xd8"
