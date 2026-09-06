"""Assertions for real desktop registration; never mutate authentication state."""

from fastapi.testclient import TestClient

from app.security.crypto import hash_token
from app.services.auth_consent import AuthConsentStore
from app.settings import get_settings


def assert_desktop_email_is_verified(client: TestClient, token: str) -> None:
    assert get_settings().app_env == "desktop"
    assert token
    store = client.app.state.auth_store
    assert isinstance(store, AuthConsentStore)
    matching = [item for item in store.email_tokens if item.token_hash == hash_token(token)]
    assert len(matching) == 1
    record = matching[0]
    assert record.used_at is not None
    user = store.users[record.user_id]
    assert user.email_verified_at is not None
    assert user.status == "active"
    # Registration already consumed this token. Reuse must remain rejected.
    response = client.post("/auth/verify-email", json={"token": token})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_token"
    assert user.status == "active"
