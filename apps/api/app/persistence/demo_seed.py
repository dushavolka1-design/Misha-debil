"""Demo account marker — seed data only for this email."""

from __future__ import annotations

from app.services.auth_consent import AuthConsentStore, UserRecord
from app.security.crypto import hash_password, utcnow

from uuid import UUID

DEMO_EMAIL = "demo@document-analyzer-rf.local"
DEMO_TENANT = UUID("00000000-0000-4000-8000-000000000001")
DEMO_USER_ID = UUID("00000000-0000-4000-8000-000000000101")


def ensure_demo_account(auth_store: AuthConsentStore) -> UserRecord | None:
    email = DEMO_EMAIL.lower()
    existing = auth_store.users_by_email.get(email)
    if existing:
        user = auth_store.users[existing]
        if not user.display_name:
            user.display_name = "Демо"
            auth_store.users[user.id] = user
        if user.display_name:
            auth_store.users_by_name[user.display_name.casefold()] = user.id
        return user

    user = UserRecord(
        id=DEMO_USER_ID,
        tenant_id=DEMO_TENANT,
        email=email,
        password_hash=hash_password("Demo-Password-12"),
        role="user",
        status="active",
        email_verified_at=utcnow(),
        display_name="Демо",
    )
    auth_store.users[user.id] = user
    auth_store.users_by_email[email] = user.id
    if user.display_name:
        auth_store.users_by_name[user.display_name.casefold()] = user.id
    return user
