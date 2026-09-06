from __future__ import annotations

import json
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from dar.providers.fake import FakePaymentProvider, sign_fake_webhook
from dar.providers.ru_payment_sandbox import RuPaymentSandboxProvider, sign_ru_sandbox_webhook
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.auth_consent import (
    REQUIRED_AT_REGISTRATION,
    AuthConsentStore,
    seed_demo_legal,
)
from app.services.billing.service import PRICE_TABLE, BillingError, BillingService, utcnow

ROOT = Path(__file__).resolve().parents[3]
LEGAL = ROOT / "legal"


@pytest.fixture()
def store() -> AuthConsentStore:
    s = AuthConsentStore()
    seed_demo_legal(s, str(LEGAL))
    return s


@pytest.fixture()
def payment() -> FakePaymentProvider:
    return FakePaymentProvider()


@pytest.fixture()
def billing(payment: FakePaymentProvider) -> BillingService:
    return BillingService(payment)


@pytest.fixture()
def client(store: AuthConsentStore, payment: FakePaymentProvider):
    app = create_app()
    with TestClient(app) as c:
        c.app.state.auth_store = store
        if not store.legal:
            seed_demo_legal(store, str(LEGAL))
        c.app.state.billing = BillingService(payment, email=c.app.state.providers.email)
        yield c


def _register(client: TestClient, store: AuthConsentStore, email: str = "bill@example.com") -> str:
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
            "email": email,
            "password": "longpassword1",
            "display_name": "Иван Тестов",
            "locale": "ru-RU",
            "accepts": accepts,
        },
    )
    assert r.status_code == 200, r.text
    token = r.json().get("verification_token_dev")
    assert token
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200
    login = client.post("/auth/login", json={"email": email, "password": "longpassword1"})
    assert login.status_code == 200
    return email


def _accept_payment_recurring(client: TestClient, store: AuthConsentStore) -> None:
    doc = store.active_legal("payment_recurring")
    assert doc
    r = client.post(
        "/privacy/consents/accept",
        json={
            "consent_id": doc.consent_id,
            "consent_version": doc.consent_version,
            "content_hash": doc.content_hash,
            "locale": "ru-RU",
        },
    )
    assert r.status_code == 200, r.text


def _signed_body(payment: FakePaymentProvider, payload: dict, *, ts: str | None = None) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload).encode()
    ts = ts or str(time.time())
    sig = sign_fake_webhook(secret=payment.webhook_secret, body=body, ts=ts)
    return body, {"x-dar-signature": sig, "x-dar-timestamp": ts}


@pytest.mark.asyncio
async def test_price_from_server_not_client(billing: BillingService) -> None:
    uid, tid = uuid4(), uuid4()
    with pytest.raises(BillingError) as ei:
        await billing.start_subscription(
            user_id=uid,
            tenant_id=tid,
            plan_code="pro",
            enable_recurring=False,
            accepted_payment_recurring=False,
            offer_version=None,
            client_amount_minor=1,  # tamper
        )
    assert ei.value.code == "price_tamper"


@pytest.mark.asyncio
async def test_idempotent_payment_intent_no_double_charge(
    billing: BillingService, payment: FakePaymentProvider
) -> None:
    uid, tid = uuid4(), uuid4()
    sub, _, _ = await billing.start_subscription(
        user_id=uid,
        tenant_id=tid,
        plan_code="free",
        enable_recurring=False,
        accepted_payment_recurring=False,
        offer_version=None,
    )
    billing.change_plan(user_id=uid, new_plan_code="pro")
    sub = billing._user_sub(uid)
    sub.status = "active"
    sub.current_period_end = utcnow()
    a1, c1 = await billing._create_attempt(sub, reason="renewal-0")
    a2, c2 = await billing._create_attempt(sub, reason="renewal-0")
    assert a1.id == a2.id
    assert c2.get("idempotent_replay") is True
    assert len(payment.intents) == 1


@pytest.mark.asyncio
async def test_forged_webhook_rejected(billing: BillingService, payment: FakePaymentProvider) -> None:
    body = json.dumps({"event_id": "e1", "event_type": "payment.succeeded"}).encode()
    with pytest.raises(BillingError) as ei:
        await billing.handle_webhook(
            headers={"x-dar-signature": "forged", "x-dar-timestamp": str(time.time())},
            raw_body=body,
        )
    assert ei.value.code == "webhook_rejected"


@pytest.mark.asyncio
async def test_duplicate_webhook_idempotent(billing: BillingService, payment: FakePaymentProvider) -> None:
    uid, tid = uuid4(), uuid4()
    sub, _, _ = await billing.start_subscription(
        user_id=uid,
        tenant_id=tid,
        plan_code="free",
        enable_recurring=False,
        accepted_payment_recurring=False,
        offer_version=None,
    )
    billing.change_plan(user_id=uid, new_plan_code="pro")
    sub = billing._user_sub(uid)
    attempt, _ = await billing._create_attempt(sub, reason="initial")
    payload = {
        "event_id": "evt-dup-1",
        "event_type": "payment.succeeded",
        "payment_ref": attempt.provider_payment_ref,
        "subscription_id": str(sub.id),
        "card_number": "4111111111111111",
    }
    body, headers = _signed_body(payment, payload)
    r1 = await billing.handle_webhook(headers=headers, raw_body=body)
    r2 = await billing.handle_webhook(headers=headers, raw_body=body)
    assert r1["status"] == "processed"
    assert r2["status"] == "duplicate"
    assert attempt.status == "succeeded"
    # PD stripped from stored payload
    raw = next(iter(billing.webhooks.values()))
    assert "card_number" not in raw.sanitized_payload


@pytest.mark.asyncio
async def test_delayed_and_reordered_webhooks(billing: BillingService, payment: FakePaymentProvider) -> None:
    uid, tid = uuid4(), uuid4()
    sub, _, _ = await billing.start_subscription(
        user_id=uid,
        tenant_id=tid,
        plan_code="free",
        enable_recurring=False,
        accepted_payment_recurring=False,
        offer_version=None,
    )
    billing.change_plan(user_id=uid, new_plan_code="pro")
    sub = billing._user_sub(uid)
    attempt, _ = await billing._create_attempt(sub, reason="initial")
    now = time.time()
    # Fail arrives first (newer), then delayed success (older occurred_at) still recorded
    fail_payload = {
        "event_id": "evt-fail",
        "event_type": "payment.failed",
        "payment_ref": attempt.provider_payment_ref,
        "subscription_id": str(sub.id),
        "occurred_at": str(now),
        "failure_code": "insufficient_funds",
    }
    ok_payload = {
        "event_id": "evt-ok-delayed",
        "event_type": "payment.succeeded",
        "payment_ref": attempt.provider_payment_ref,
        "subscription_id": str(sub.id),
        "occurred_at": str(now - 60),
    }
    b1, h1 = _signed_body(payment, fail_payload, ts=str(now))
    await billing.handle_webhook(headers=h1, raw_body=b1, now_ts=now)
    assert sub.status == "past_due"
    b2, h2 = _signed_body(payment, ok_payload, ts=str(now))
    await billing.handle_webhook(headers=h2, raw_body=b2, now_ts=now)
    assert attempt.status == "succeeded"
    assert sub.status == "active"


@pytest.mark.asyncio
async def test_timestamp_skew_rejected(billing: BillingService, payment: FakePaymentProvider) -> None:
    body = json.dumps({"event_id": "e-old", "event_type": "payment.succeeded"}).encode()
    old_ts = str(time.time() - 10_000)
    sig = sign_fake_webhook(secret=payment.webhook_secret, body=body, ts=old_ts)
    with pytest.raises(BillingError) as ei:
        await billing.handle_webhook(
            headers={"x-dar-signature": sig, "x-dar-timestamp": old_ts},
            raw_body=body,
        )
    assert "timestamp" in (ei.value.message or "")


@pytest.mark.asyncio
async def test_cancel_renew_race(billing: BillingService) -> None:
    uid, tid = uuid4(), uuid4()
    sub, _, _ = await billing.start_subscription(
        user_id=uid,
        tenant_id=tid,
        plan_code="pro",
        enable_recurring=True,
        accepted_payment_recurring=True,
        offer_version=None,
    )
    sub.recurring_enabled = True
    sub.status = "active"
    sub.next_renewal_at = utcnow() - timedelta(seconds=1)
    billing.cancel_at_period_end(user_id=uid)
    results = await billing.process_renewals(now=utcnow() + timedelta(days=40))
    actions = [r["action"] for r in results]
    assert "renewal_attempt" not in actions
    assert "expired" in actions or sub.cancellation_at_period_end


@pytest.mark.asyncio
async def test_refund_no_fake_receipt(billing: BillingService) -> None:
    uid, tid = uuid4(), uuid4()
    await billing.start_subscription(
        user_id=uid,
        tenant_id=tid,
        plan_code="free",
        enable_recurring=False,
        accepted_payment_recurring=False,
        offer_version=None,
    )
    billing.change_plan(user_id=uid, new_plan_code="pro")
    sub = billing._user_sub(uid)
    attempt, _ = await billing._create_attempt(sub, reason="initial")
    attempt.status = "succeeded"
    rec = await billing.request_refund(user_id=uid, payment_attempt_id=attempt.id)
    assert rec.status == "succeeded"
    assert attempt.status == "refunded"
    # Never invent fiscal receipt
    assert getattr(rec, "receipt", None) is None


@pytest.mark.asyncio
async def test_price_change_uses_server_table(billing: BillingService) -> None:
    uid, tid = uuid4(), uuid4()
    await billing.start_subscription(
        user_id=uid,
        tenant_id=tid,
        plan_code="pro",
        enable_recurring=False,
        accepted_payment_recurring=False,
        offer_version=None,
    )
    sub = billing.change_plan(user_id=uid, new_plan_code="pro_annual")
    assert sub.amount_minor == PRICE_TABLE["pro_annual"].amount_minor
    assert sub.price_version == PRICE_TABLE["pro_annual"].price_version


@pytest.mark.asyncio
async def test_trial_no_charge_without_recurring(billing: BillingService) -> None:
    uid, tid = uuid4(), uuid4()
    sub, attempt, checkout = await billing.start_subscription(
        user_id=uid,
        tenant_id=tid,
        plan_code="pro",
        enable_recurring=False,
        accepted_payment_recurring=False,
        offer_version=None,
    )
    assert sub.status == "trialing"
    assert attempt is None
    assert checkout["mode"] == "trial" or sub.trial_ends_at
    # Force trial end without recurring
    sub.trial_ends_at = utcnow() - timedelta(seconds=1)
    results = await billing.process_renewals(now=utcnow())
    assert any(r["action"] == "trial_ended_no_charge" for r in results)
    assert sub.status == "expired"


@pytest.mark.asyncio
async def test_trial_notice_and_conversion_requires_recurring(billing: BillingService) -> None:
    uid, tid = uuid4(), uuid4()
    sub, _, _ = await billing.start_subscription(
        user_id=uid,
        tenant_id=tid,
        plan_code="pro",
        enable_recurring=True,
        accepted_payment_recurring=True,
        offer_version=None,
    )
    assert sub.recurring_enabled
    sub.trial_ends_at = utcnow() + timedelta(days=1)
    await billing.process_renewals(now=utcnow())
    assert sub.trial_notice_sent_at is not None
    assert any(a.action == "trial_notice_queued" or a.action == "trial_notice_skipped_no_email" for a in billing.audit)


@pytest.mark.asyncio
async def test_provider_outage(billing: BillingService, payment: FakePaymentProvider) -> None:
    uid, tid = uuid4(), uuid4()
    await billing.start_subscription(
        user_id=uid,
        tenant_id=tid,
        plan_code="free",
        enable_recurring=False,
        accepted_payment_recurring=False,
        offer_version=None,
    )
    billing.change_plan(user_id=uid, new_plan_code="pro")
    sub = billing._user_sub(uid)
    payment.outage = True
    with pytest.raises(RuntimeError, match="provider_outage"):
        await billing._create_attempt(sub, reason="outage-test")


@pytest.mark.asyncio
async def test_dunning_limited_attempts(billing: BillingService, payment: FakePaymentProvider) -> None:
    uid, tid = uuid4(), uuid4()
    await billing.start_subscription(
        user_id=uid,
        tenant_id=tid,
        plan_code="free",
        enable_recurring=False,
        accepted_payment_recurring=False,
        offer_version=None,
    )
    billing.change_plan(user_id=uid, new_plan_code="pro")
    sub = billing._user_sub(uid)
    attempt, _ = await billing._create_attempt(sub, reason="dunning")
    for i in range(3):
        payload = {
            "event_id": f"fail-{i}",
            "event_type": "payment.failed",
            "payment_ref": attempt.provider_payment_ref,
            "subscription_id": str(sub.id),
        }
        body, headers = _signed_body(payment, payload)
        await billing.handle_webhook(headers=headers, raw_body=body)
    assert sub.dunning_attempts == 3
    assert sub.status == "expired"
    hist = billing.history(user_id=uid)
    assert all("card" not in str(p).lower() for p in hist["payments"])


@pytest.mark.asyncio
async def test_ru_sandbox_live_mode_blocked() -> None:
    with pytest.raises(RuntimeError, match="disabled until credentials"):
        RuPaymentSandboxProvider(live_mode=True, shop_id="x", secret="y")


@pytest.mark.asyncio
async def test_ru_sandbox_webhook_signature() -> None:
    p = RuPaymentSandboxProvider(live_mode=False)
    billing = BillingService(p)
    payload = {"event_id": "ru1", "event_type": "payment.succeeded"}
    body = json.dumps(payload).encode()
    ts = str(time.time())
    sig = sign_ru_sandbox_webhook(secret=p.webhook_secret, body=body, ts=ts)
    r = await billing.handle_webhook(
        headers={"x-ru-payment-signature": sig, "x-ru-payment-timestamp": ts},
        raw_body=body,
    )
    assert r["status"] == "processed"


def test_api_plans_subscribe_cancel_history(client: TestClient, store: AuthConsentStore) -> None:
    _register(client, store)
    plans = client.get("/billing/plans")
    assert plans.status_code == 200
    assert any(p["plan_code"] == "pro" for p in plans.json())
    # client amount tamper
    bad = client.post("/billing/subscribe", json={"plan_code": "pro", "client_amount_minor": 1})
    assert bad.status_code == 400
    assert bad.json()["detail"]["code"] == "price_tamper"
    ok = client.post("/billing/subscribe", json={"plan_code": "pro"})
    assert ok.status_code == 200
    assert ok.json()["subscription"]["status"] == "trialing"
    _accept_payment_recurring(client, store)
    price = PRICE_TABLE["pro"]
    en = client.post(
        "/billing/recurring/enable",
        json={
            "accepted": True,
            "shown_amount_minor": price.amount_minor,
            "shown_period_days": price.period_days,
            "shown_next_charge_at": ok.json()["subscription"]["current_period_end"],
        },
    )
    assert en.status_code == 200
    assert en.json()["cancel_path"] == "/app/billing"
    cancel = client.post("/billing/cancel")
    assert cancel.status_code == 200
    assert "access_until" in cancel.json()
    me = client.get("/billing/me")
    assert me.status_code == 200
    assert me.json()["subscription"]["cancellation_at_period_end"] is True
    assert me.json()["delete_account_path"] == "/app/profile"
    # remove payment method is explicit
    rm = client.post("/billing/payment-method/remove")
    assert rm.status_code == 200


def test_admin_reconciliation(client: TestClient, store: AuthConsentStore) -> None:
    _register(client, store, email="admin@example.com")
    # promote
    user = next(u for u in store.users.values() if u.email == "admin@example.com")
    user.role = "admin"
    client.post("/billing/subscribe", json={"plan_code": "free"})
    r = client.get("/billing/admin/reconciliation")
    assert r.status_code == 200
    data = r.json()
    assert "audit_tail" in data
    assert data["provider"] == "fake_payment"
    assert data["capabilities"]["receipts"] is False


@pytest.mark.asyncio
async def test_approved_offer_gate(billing: BillingService) -> None:
    billing.require_approved_offer = True
    billing.approved_offer_version = "2026.08.11.2"
    with pytest.raises(BillingError) as ei:
        await billing.start_subscription(
            user_id=uuid4(),
            tenant_id=uuid4(),
            plan_code="pro",
            enable_recurring=False,
            accepted_payment_recurring=False,
            offer_version="wrong",
        )
    assert ei.value.code == "offer_not_approved"
