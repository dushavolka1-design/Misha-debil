from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from dar.providers.fake import FakePaymentProvider
from fastapi.testclient import TestClient

from app.main import create_app
from app.security.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState
from app.services.auth_consent import REQUIRED_AT_REGISTRATION, AuthConsentStore, seed_demo_legal
from app.services.sources.url_policy import UrlPolicyError, load_allowlist, validate_url

ROOT = Path(__file__).resolve().parents[3]
LEGAL = ROOT / "legal"


@pytest.fixture()
def store() -> AuthConsentStore:
    s = AuthConsentStore()
    seed_demo_legal(s, str(LEGAL))
    return s


@pytest.fixture()
def client(store: AuthConsentStore):
    app = create_app()
    with TestClient(app) as c:
        c.app.state.auth_store = store
        yield c


def test_ssrf_blocks_private_and_metadata() -> None:
    cfg = load_allowlist()
    for bad in (
        "http://127.0.0.1/secret",
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.1.1/",
        "http://[::1]/",
    ):
        with pytest.raises(UrlPolicyError):
            validate_url(bad, cfg=cfg)


def test_rate_limiter_blocks() -> None:
    from app.security.rate_limit import RateLimiter

    rl = RateLimiter()
    key = f"t-{uuid4()}"
    assert rl.hit(key, limit=3, window_seconds=60)
    assert rl.hit(key, limit=3, window_seconds=60)
    assert rl.hit(key, limit=3, window_seconds=60)
    assert not rl.hit(key, limit=3, window_seconds=60)


def test_idor_document_access() -> None:
    from dar.providers.fake import FakeKMSProvider, FakeMalwareScanner, InMemoryObjectStorage

    from app.services.upload.fsm import DocumentState
    from app.services.upload.lifecycle import (
        DocumentLifecycleService,
        DocumentRecord,
        DocumentStore,
        UploadError,
    )
    from app.services.upload.retention import RetentionPolicy

    owner = uuid4()
    other = uuid4()
    doc = DocumentRecord(
        id=uuid4(),
        user_id=owner,
        tenant_id=uuid4(),
        state=DocumentState.READY,
        display_name="x.pdf",
        declared_content_type="application/pdf",
        expected_checksum=None,
    )
    svc = DocumentLifecycleService(
        DocumentStore(),
        storage=InMemoryObjectStorage(),
        malware=FakeMalwareScanner(),
        kms=FakeKMSProvider(),
        bucket_quarantine="q",
        bucket_originals="o",
        bucket_derived="d",
        bucket_reports="r",
        retention=RetentionPolicy(30, 60, 60, 90, 365),
        presign_secret="test",
    )
    svc.assert_document_access(doc, user_id=owner, user_role="user")
    with pytest.raises(UploadError) as ei:
        svc.assert_document_access(doc, user_id=other, user_role="user")
    assert ei.value.code == "access_denied"


def test_csrf_origin_rejected_with_session(client: TestClient, store: AuthConsentStore) -> None:
    # Register + login
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
    r = client.post(
        "/auth/register",
        json={
            "email": "csrf@example.com",
            "password": "longpassword1",
            "display_name": "Иван Тестов",
            "locale": "ru-RU",
            "accepts": accepts,
        },
    )
    assert r.status_code == 200
    token = r.json()["verification_token_dev"]
    client.post("/auth/verify-email", json={"token": token})
    login = client.post("/auth/login", json={"email": "csrf@example.com", "password": "longpassword1"})
    assert login.status_code == 200
    bad = client.post(
        "/billing/cancel",
        headers={"Origin": "https://evil.example"},
    )
    assert bad.status_code == 403
    assert bad.json()["code"] == "csrf_origin_rejected"


def test_audit_append_only_consent(store: AuthConsentStore) -> None:
    from app.services.auth_consent import AppendOnlyViolation

    with pytest.raises(AppendOnlyViolation):
        store.delete_consent_event(uuid4())


def test_payment_provider_outage_flag() -> None:
    p = FakePaymentProvider()
    p.outage = True
    import asyncio
    from uuid import uuid4 as u

    async def _run() -> None:
        with pytest.raises(RuntimeError, match="provider_outage"):
            await p.create_payment_intent(
                user_id=u(),
                plan_code="pro",
                amount_minor=1,
                currency="RUB",
                idempotency_key="k",
                description="t",
            )

    asyncio.run(_run())


def test_circuit_breaker_opens() -> None:
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=60, name="llm")
    cb.before_call()
    cb.record_failure()
    cb.before_call()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        cb.before_call()
