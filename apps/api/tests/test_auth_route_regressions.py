"""Real auth routes with synthetic consent data; no external services required."""

from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import auth
from app.security.crypto import utcnow
from app.security.rate_limit import RateLimiter
from app.services.auth_consent import REQUIRED_AT_REGISTRATION, AuthConsentStore
from app.settings import Settings, get_settings


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    application = FastAPI()
    application.include_router(auth.router)
    application.state.auth_store = AuthConsentStore()
    # Reset only the test's limiter, not production thresholds or behavior.
    monkeypatch.setattr(auth, "rate_limiter", RateLimiter())
    application.dependency_overrides[get_settings] = lambda: Settings.model_construct(app_env="test")
    for consent_id in REQUIRED_AT_REGISTRATION:
        application.state.auth_store.publish_legal(
            consent_id=consent_id,
            consent_version="synthetic-test-v1",
            locale="ru-RU",
            canonical_text="Synthetic consent fixture; not a legal publication.",
            body_path="synthetic",
            reviewer_id="synthetic-test",
        )
    return application


def registration(app: FastAPI) -> dict[str, object]:
    store = app.state.auth_store
    accepts = []
    for consent_id in REQUIRED_AT_REGISTRATION:
        doc = store.active_legal(consent_id)
        assert doc is not None
        accepts.append(
            {
                "consent_id": doc.consent_id,
                "consent_version": doc.consent_version,
                "content_hash": doc.content_hash,
            }
        )
    return {
        "email": "synthetic-auth@example.com",
        "password": "Synthetic-password-752",
        "display_name": "Тестовый Пользователь",
        "locale": "ru-RU",
        "accepts": accepts,
    }


def test_registration_limit_returns_429_without_unhandled_exception(app: FastAPI) -> None:
    payload = registration(app)
    payload["accepts"] = []
    with TestClient(app) as client:
        for _ in range(5):
            response = client.post("/auth/register", json=payload)
            assert response.status_code == 400
            assert response.json()["detail"]["code"] == "consents_required"
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 429
        assert response.json()["detail"]["code"] == "rate_limited"
        assert not app.state.auth_store.users
        assert not app.state.auth_store.email_tokens


def test_test_mode_verification_is_single_use(app: FastAPI) -> None:
    with TestClient(app) as client:
        response = client.post("/auth/register", json=registration(app))
        assert response.status_code == 200
        token = response.json()["verification_token_dev"]
        assert token
        user = next(iter(app.state.auth_store.users.values()))
        assert user.status == "pending_verification"
        assert user.email_verified_at is None
        assert client.post("/auth/verify-email", json={"token": token}).status_code == 200
        assert user.status == "active"
        assert user.email_verified_at is not None
        replay = client.post("/auth/verify-email", json={"token": token})
        assert replay.status_code == 400
        assert replay.json()["detail"]["code"] == "invalid_token"


def test_expired_verification_does_not_activate_user(app: FastAPI) -> None:
    with TestClient(app) as client:
        response = client.post("/auth/register", json=registration(app))
        assert response.status_code == 200
        token = response.json()["verification_token_dev"]
        app.state.auth_store.email_tokens[0].expires_at = utcnow() - timedelta(seconds=1)
        assert client.post("/auth/verify-email", json={"token": token}).status_code == 400
        user = next(iter(app.state.auth_store.users.values()))
        assert user.status == "pending_verification"
        assert user.email_verified_at is None


@pytest.mark.parametrize("mode", ["desktop", "local"])
def test_offline_modes_already_consume_verification(app: FastAPI, mode: str) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings.model_construct(app_env=mode)
    with TestClient(app) as client:
        response = client.post("/auth/register", json=registration(app))
        assert response.status_code == 200
        user = next(iter(app.state.auth_store.users.values()))
        assert user.status == "active"
        assert user.email_verified_at is not None
        token = response.json()["verification_token_dev"]
        assert client.post("/auth/verify-email", json={"token": token}).status_code == 400


def test_production_does_not_auto_verify_or_disclose_token(app: FastAPI) -> None:
    # Route-level contract only; does not bypass the real app's production gates.
    app.dependency_overrides[get_settings] = lambda: Settings.model_construct(app_env="production")
    with TestClient(app) as client:
        response = client.post("/auth/register", json=registration(app))
        assert response.status_code == 200
        assert response.json().get("verification_token_dev") is None
        user = next(iter(app.state.auth_store.users.values()))
        assert user.status == "pending_verification"
        assert user.email_verified_at is None
        login = client.post(
            "/auth/login",
            json={"email": "synthetic-auth@example.com", "password": "Synthetic-password-752"},
        )
        assert login.status_code == 401
        assert not app.state.auth_store.sessions


@pytest.mark.parametrize("path", ["/auth/me", "/auth/me/avatar"])
def test_typed_user_dependency_still_rejects_anonymous(app: FastAPI, path: str) -> None:
    with TestClient(app) as client:
        response = client.get(path)
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "unauthorized"
