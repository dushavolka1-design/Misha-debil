from __future__ import annotations

"""Server-side subscription/billing — price table never trusted from client."""

import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from dar.providers.ports import PaymentProvider


BILLING_ENGINE_VERSION = "billing.engine.v1"
MAX_DUNNING_ATTEMPTS = 3
WEBHOOK_RAW_RETENTION_DAYS = 30
TRIAL_NOTICE_DAYS_BEFORE = 3


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BillingError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass(frozen=True)
class PriceVersion:
    plan_code: str
    price_version: str
    amount_minor: int
    currency: str
    period_days: int
    trial_days: int
    label: str
    active: bool = True


# Server price table — client cannot override amounts
PRICE_TABLE: dict[str, PriceVersion] = {
    "free": PriceVersion("free", "2026.08.1", 0, "RUB", 30, 0, "Free", active=True),
    "pro": PriceVersion("pro", "2026.08.1", 99000, "RUB", 30, 7, "Pro monthly", active=True),
    "pro_annual": PriceVersion("pro_annual", "2026.08.1", 990000, "RUB", 365, 7, "Pro annual", active=True),
}


@dataclass
class SubscriptionRecord:
    id: UUID
    user_id: UUID
    tenant_id: UUID
    plan_code: str
    price_version: str
    amount_minor: int
    currency: str
    status: str  # trialing|active|past_due|cancelled|expired
    provider_ref: str | None
    trial_ends_at: datetime | None
    current_period_end: datetime
    cancellation_at_period_end: bool = False
    cancelled_at: datetime | None = None
    next_renewal_at: datetime | None = None
    recurring_enabled: bool = False
    payment_method_ref: str | None = None  # opaque token only — never PAN
    dunning_attempts: int = 0
    trial_notice_sent_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class PaymentAttempt:
    id: UUID
    subscription_id: UUID
    user_id: UUID
    amount_minor: int
    currency: str
    status: str  # pending|succeeded|failed|refunded
    provider_payment_ref: str
    idempotency_key: str
    failure_code: str | None = None
    receipt_ref: str | None = None  # only from provider capability — never invented
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class RefundRecord:
    id: UUID
    payment_attempt_id: UUID
    provider_refund_ref: str | None
    amount_minor: int
    status: str  # requested|succeeded|rejected|needs_review
    reason: str
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class WebhookRawEvent:
    id: UUID
    provider: str
    event_id: str
    event_type: str
    received_at: datetime
    occurred_at: datetime | None
    raw_hash: str
    sanitized_payload: dict[str, Any]
    processed: bool = False
    process_error: str | None = None


@dataclass
class BillingAudit:
    id: UUID
    at: datetime
    actor: str
    action: str
    detail: dict[str, Any]


class BillingService:
    def __init__(self, payment: PaymentProvider, *, email: Any | None = None) -> None:
        self.payment = payment
        self.email = email
        self.subscriptions: dict[UUID, SubscriptionRecord] = {}
        self.by_user: dict[UUID, UUID] = {}
        self.attempts: dict[UUID, PaymentAttempt] = {}
        self.attempts_by_idem: dict[str, UUID] = {}
        self.refunds: list[RefundRecord] = []
        self.webhooks: dict[str, WebhookRawEvent] = {}  # key = provider:event_id
        self.seen_replay: set[str] = set()  # raw_hash+event_id
        self.audit: list[BillingAudit] = []
        self.require_approved_offer: bool = False
        self.approved_offer_version: str | None = None

    def list_plans(self) -> list[dict[str, Any]]:
        return [
            {
                "plan_code": p.plan_code,
                "price_version": p.price_version,
                "amount_minor": p.amount_minor,
                "currency": p.currency,
                "period_days": p.period_days,
                "trial_days": p.trial_days,
                "label": p.label,
            }
            for p in PRICE_TABLE.values()
            if p.active
        ]

    def get_price(self, plan_code: str) -> PriceVersion:
        price = PRICE_TABLE.get(plan_code)
        if not price or not price.active:
            raise BillingError("unknown_plan", "Plan not found in server price table", http_status=404)
        return price

    def _audit(self, actor: str, action: str, **detail: Any) -> None:
        self.audit.append(
            BillingAudit(id=uuid4(), at=utcnow(), actor=actor, action=action, detail=detail),
        )

    async def start_subscription(
        self,
        *,
        user_id: UUID,
        tenant_id: UUID,
        plan_code: str,
        enable_recurring: bool,
        accepted_payment_recurring: bool,
        offer_version: str | None,
        client_amount_minor: int | None = None,
    ) -> tuple[SubscriptionRecord, PaymentAttempt | None, dict[str, Any]]:
        if self.require_approved_offer:
            if not offer_version or offer_version != self.approved_offer_version:
                raise BillingError("offer_not_approved", "Approved offer version required", http_status=403)
        price = self.get_price(plan_code)
        # Never trust client amount
        if client_amount_minor is not None and client_amount_minor != price.amount_minor:
            raise BillingError("price_tamper", "Client amount does not match server price table", http_status=400)
        if enable_recurring and not accepted_payment_recurring:
            raise BillingError(
                "recurring_consent_required", "Separate payment_recurring consent required", http_status=403
            )
        if price.amount_minor > 0 and enable_recurring and not accepted_payment_recurring:
            raise BillingError("recurring_consent_required", "Recurring consent required", http_status=403)

        now = utcnow()
        trial_end = now + timedelta(days=price.trial_days) if price.trial_days > 0 else None
        period_end = trial_end or (now + timedelta(days=price.period_days))
        sub = SubscriptionRecord(
            id=uuid4(),
            user_id=user_id,
            tenant_id=tenant_id,
            plan_code=price.plan_code,
            price_version=price.price_version,
            amount_minor=price.amount_minor,
            currency=price.currency,
            status="trialing" if trial_end else ("active" if price.amount_minor == 0 else "pending"),
            provider_ref=None,
            trial_ends_at=trial_end,
            current_period_end=period_end,
            next_renewal_at=period_end if enable_recurring else None,
            recurring_enabled=enable_recurring and price.amount_minor > 0,
        )
        self.subscriptions[sub.id] = sub
        self.by_user[user_id] = sub.id
        self._audit(str(user_id), "subscription_started", plan=plan_code, price_version=price.price_version)

        attempt = None
        checkout: dict[str, Any] = {}
        if price.amount_minor > 0 and not trial_end:
            attempt, checkout = await self._create_attempt(sub, reason="initial")
            sub.status = "pending"
        elif price.amount_minor > 0 and trial_end:
            # Trial first — never convert free trial to paid without confirmed recurring acceptance
            checkout = {
                "mode": "trial",
                "trial_ends_at": trial_end.isoformat(),
                "next_charge_amount_minor": price.amount_minor if enable_recurring else None,
                "next_charge_at": trial_end.isoformat() if enable_recurring else None,
                "recurring_enabled": enable_recurring,
                "cancel_path": "/app/billing",
                "message": (
                    "Trial active; paid conversion requires confirmed recurring acceptance"
                    if enable_recurring
                    else "Trial active; no charge without separate recurring enablement"
                ),
            }
        else:
            sub.status = "active"
            checkout = {"mode": "free", "status": "active"}

        return sub, attempt, checkout

    async def _create_attempt(self, sub: SubscriptionRecord, *, reason: str) -> tuple[PaymentAttempt, dict[str, Any]]:
        idem = hashlib.sha256(
            f"{sub.id}:{sub.price_version}:{reason}:{sub.current_period_end.isoformat()}".encode()
        ).hexdigest()
        if idem in self.attempts_by_idem:
            existing = self.attempts[self.attempts_by_idem[idem]]
            return existing, {"idempotent_replay": True, "provider_ref": existing.provider_payment_ref}

        session = await self.payment.create_payment_intent(
            user_id=sub.user_id,
            plan_code=sub.plan_code,
            amount_minor=sub.amount_minor,
            currency=sub.currency,
            idempotency_key=idem,
            description=f"{sub.plan_code} {sub.price_version}",
            metadata={"subscription_id": str(sub.id), "reason": reason},
        )
        attempt = PaymentAttempt(
            id=uuid4(),
            subscription_id=sub.id,
            user_id=sub.user_id,
            amount_minor=sub.amount_minor,
            currency=sub.currency,
            status="pending",
            provider_payment_ref=session.provider_ref,
            idempotency_key=idem,
        )
        self.attempts[attempt.id] = attempt
        self.attempts_by_idem[idem] = attempt.id
        sub.provider_ref = session.provider_ref
        self._audit(str(sub.user_id), "payment_intent_created", attempt_id=str(attempt.id), amount=sub.amount_minor)
        return attempt, {
            "checkout_url": session.checkout_url,
            "provider_ref": session.provider_ref,
            "amount_minor": session.amount_minor or sub.amount_minor,
            "currency": session.currency or sub.currency,
            "idempotency_key": idem,
        }

    def enable_recurring_explicit(
        self,
        *,
        user_id: UUID,
        accepted: bool,
        shown_amount_minor: int,
        shown_period_days: int,
        shown_next_charge_at: str,
    ) -> SubscriptionRecord:
        """Separate clear action: amount, period, next charge, cancel path."""
        sub = self._user_sub(user_id)
        price = self.get_price(sub.plan_code)
        if not accepted:
            raise BillingError("recurring_not_accepted", "Recurring not accepted")
        if shown_amount_minor != price.amount_minor:
            raise BillingError("price_tamper", "Shown amount must match server price", http_status=400)
        if shown_period_days != price.period_days:
            raise BillingError("period_mismatch", "Shown period must match plan", http_status=400)
        sub.recurring_enabled = True
        sub.next_renewal_at = sub.current_period_end
        sub.updated_at = utcnow()
        self._audit(
            str(user_id),
            "recurring_enabled",
            amount_minor=shown_amount_minor,
            period_days=shown_period_days,
            next_charge_at=shown_next_charge_at,
            cancel_path="/app/billing",
        )
        return sub

    def cancel_at_period_end(self, *, user_id: UUID) -> SubscriptionRecord:
        sub = self._user_sub(user_id)
        sub.cancellation_at_period_end = True
        sub.cancelled_at = utcnow()
        sub.recurring_enabled = False
        sub.next_renewal_at = None
        sub.updated_at = utcnow()
        self._audit(str(user_id), "cancel_at_period_end", access_until=sub.current_period_end.isoformat())
        return sub

    def remove_payment_method(self, *, user_id: UUID) -> SubscriptionRecord:
        sub = self._user_sub(user_id)
        sub.payment_method_ref = None
        sub.recurring_enabled = False
        sub.updated_at = utcnow()
        self._audit(str(user_id), "payment_method_removed")
        return sub

    def history(self, *, user_id: UUID) -> dict[str, Any]:
        sub_id = self.by_user.get(user_id)
        sub = self.subscriptions.get(sub_id) if sub_id else None
        attempts = [a for a in self.attempts.values() if a.user_id == user_id]
        return {
            "subscription": self._sub_public(sub) if sub else None,
            "payments": [
                {
                    "id": str(a.id),
                    "amount_minor": a.amount_minor,
                    "currency": a.currency,
                    "status": a.status,
                    "receipt_ref": a.receipt_ref,
                    "created_at": a.created_at.isoformat(),
                    # never expose PAN / full provider secrets
                }
                for a in sorted(attempts, key=lambda x: x.created_at, reverse=True)
            ],
            "cancel_path": "/app/billing",
            "delete_account_path": "/app/profile",
        }

    async def handle_webhook(
        self,
        *,
        headers: dict[str, str],
        raw_body: bytes,
        now_ts: float | None = None,
    ) -> dict[str, Any]:
        verification = self.payment.verify_webhook(headers=headers, raw_body=raw_body, now_ts=now_ts)
        if not verification.ok:
            self._audit("webhook", "rejected", reason=verification.reason)
            raise BillingError("webhook_rejected", verification.reason or "rejected", http_status=401)

        event_id = verification.event_id or ""
        if not event_id:
            raise BillingError("webhook_rejected", "missing event_id", http_status=400)

        raw_hash = hashlib.sha256(raw_body).hexdigest()
        replay_key = f"{self.payment.name}:{event_id}:{raw_hash}"
        if replay_key in self.seen_replay:
            return {"status": "duplicate", "event_id": event_id}
        self.seen_replay.add(replay_key)

        key = f"{self.payment.name}:{event_id}"
        if key in self.webhooks:
            # Idempotency: same provider event id
            return {"status": "duplicate", "event_id": event_id}

        occurred = None
        if verification.occurred_at:
            try:
                occurred = datetime.fromtimestamp(float(verification.occurred_at), tz=timezone.utc)
            except Exception:  # noqa: BLE001
                try:
                    occurred = datetime.fromisoformat(verification.occurred_at.replace("Z", "+00:00"))
                except Exception:  # noqa: BLE001
                    occurred = None

        raw = WebhookRawEvent(
            id=uuid4(),
            provider=self.payment.name,
            event_id=event_id,
            event_type=verification.event_type or "unknown",
            received_at=utcnow(),
            occurred_at=occurred,
            raw_hash=raw_hash,
            sanitized_payload=dict(verification.sanitized_payload),
        )
        self.webhooks[key] = raw

        # Out-of-order: if event older than last processed for subscription, still record but apply carefully
        try:
            self._apply_webhook(raw)
            raw.processed = True
        except Exception as exc:  # noqa: BLE001
            raw.process_error = str(exc)
            self._audit("webhook", "process_error", event_id=event_id, error=str(exc))
            raise

        return {"status": "processed", "event_id": event_id, "event_type": raw.event_type}

    def _apply_webhook(self, raw: WebhookRawEvent) -> None:
        payload = raw.sanitized_payload
        sub_id_raw = payload.get("subscription_id")
        payment_ref = payload.get("payment_ref") or payload.get("provider_payment_ref")
        etype = raw.event_type

        sub = None
        if sub_id_raw:
            try:
                sub = self.subscriptions.get(UUID(str(sub_id_raw)))
            except Exception:  # noqa: BLE001
                sub = None
        if not sub and payment_ref:
            for s in self.subscriptions.values():
                if s.provider_ref == payment_ref:
                    sub = s
                    break

        # Find attempt
        attempt = None
        if payment_ref:
            for a in self.attempts.values():
                if a.provider_payment_ref == payment_ref:
                    attempt = a
                    break

        if etype in {"payment.succeeded", "payment.captured"}:
            if attempt and attempt.status == "succeeded":
                return  # already applied — no double charge side-effects
            if attempt:
                attempt.status = "succeeded"
                # Receipt only if provider capability says so — never invent fiscal receipt
                caps = self.payment.capabilities()
                if caps.receipts and payload.get("receipt_ref"):
                    attempt.receipt_ref = str(payload["receipt_ref"])
                else:
                    attempt.receipt_ref = None
            if sub:
                # Out-of-order guard: ignore success if already cancelled and period ended
                if sub.status == "expired":
                    return
                sub.status = "active"
                sub.dunning_attempts = 0
                price = self.get_price(sub.plan_code)
                # Extend period from max(now, current_period_end) for delayed events
                base = max(utcnow(), sub.current_period_end)
                sub.current_period_end = base + timedelta(days=price.period_days)
                if sub.recurring_enabled and not sub.cancellation_at_period_end:
                    sub.next_renewal_at = sub.current_period_end
                sub.updated_at = utcnow()
            self._audit("webhook", "payment_succeeded", event_id=raw.event_id)

        elif etype in {"payment.failed", "payment.canceled"}:
            if attempt and attempt.status != "succeeded":
                attempt.status = "failed"
                attempt.failure_code = str(payload.get("failure_code") or "provider_failed")
            if sub:
                sub.dunning_attempts += 1
                sub.status = "past_due" if sub.dunning_attempts < MAX_DUNNING_ATTEMPTS else "expired"
                sub.updated_at = utcnow()
            self._audit(
                "webhook", "payment_failed", event_id=raw.event_id, attempts=sub.dunning_attempts if sub else None
            )

        elif etype == "subscription.cancelled":
            if sub:
                sub.status = "cancelled"
                sub.recurring_enabled = False
                sub.cancellation_at_period_end = True
                sub.updated_at = utcnow()

        elif etype == "refund.succeeded":
            if attempt:
                attempt.status = "refunded"
            self._audit("webhook", "refund_succeeded", event_id=raw.event_id)

    async def process_renewals(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        now = now or utcnow()
        results = []
        for sub in list(self.subscriptions.values()):
            if sub.cancellation_at_period_end and now >= sub.current_period_end:
                sub.status = "expired"
                results.append({"subscription_id": str(sub.id), "action": "expired"})
                continue
            # Trial notice
            if (
                sub.trial_ends_at
                and sub.trial_notice_sent_at is None
                and now >= sub.trial_ends_at - timedelta(days=TRIAL_NOTICE_DAYS_BEFORE)
            ):
                await self._send_trial_notice(sub)
                sub.trial_notice_sent_at = now
                results.append({"subscription_id": str(sub.id), "action": "trial_notice"})
            # Convert trial → paid only if recurring explicitly enabled
            if sub.status == "trialing" and sub.trial_ends_at and now >= sub.trial_ends_at:
                if not sub.recurring_enabled:
                    sub.status = "expired"
                    results.append({"subscription_id": str(sub.id), "action": "trial_ended_no_charge"})
                    continue
                attempt, _ = await self._create_attempt(sub, reason="trial_conversion")
                sub.status = "pending"
                results.append({"subscription_id": str(sub.id), "action": "trial_charge", "attempt": str(attempt.id)})
                continue
            # Renewal
            if (
                sub.recurring_enabled
                and not sub.cancellation_at_period_end
                and sub.next_renewal_at
                and now >= sub.next_renewal_at
                and sub.status in {"active", "past_due"}
            ):
                if sub.dunning_attempts >= MAX_DUNNING_ATTEMPTS:
                    sub.status = "expired"
                    results.append({"subscription_id": str(sub.id), "action": "dunning_exhausted"})
                    continue
                attempt, _ = await self._create_attempt(sub, reason=f"renewal-{sub.dunning_attempts}")
                results.append(
                    {"subscription_id": str(sub.id), "action": "renewal_attempt", "attempt": str(attempt.id)}
                )
        return results

    async def _send_trial_notice(self, sub: SubscriptionRecord) -> None:
        if not self.email:
            self._audit("system", "trial_notice_skipped_no_email", subscription_id=str(sub.id))
            return
        # Email provider doesn't know user email here — audit only; real wiring uses user store
        self._audit(
            "system",
            "trial_notice_queued",
            subscription_id=str(sub.id),
            trial_ends_at=sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
            next_amount_minor=sub.amount_minor if sub.recurring_enabled else 0,
        )

    async def request_refund(self, *, user_id: UUID, payment_attempt_id: UUID) -> RefundRecord:
        attempt = self.attempts.get(payment_attempt_id)
        if not attempt or attempt.user_id != user_id:
            raise BillingError("not_found", "Payment not found", http_status=404)
        caps = self.payment.capabilities()
        if not caps.refunds:
            rec = RefundRecord(
                id=uuid4(),
                payment_attempt_id=attempt.id,
                provider_refund_ref=None,
                amount_minor=attempt.amount_minor,
                status="needs_review",
                reason="provider_refunds_require_legal_accounting_review",
            )
            self.refunds.append(rec)
            # Never invent fiscal receipt
            self._audit(str(user_id), "refund_needs_review", attempt_id=str(attempt.id))
            return rec
        result = await self.payment.request_refund(provider_payment_ref=attempt.provider_payment_ref)
        rec = RefundRecord(
            id=uuid4(),
            payment_attempt_id=attempt.id,
            provider_refund_ref=result.get("refund_ref"),
            amount_minor=attempt.amount_minor,
            status="succeeded" if result.get("ok") else "rejected",
            reason=str(result.get("note") or result.get("reason") or ""),
        )
        self.refunds.append(rec)
        if rec.status == "succeeded":
            attempt.status = "refunded"
        return rec

    def change_plan(self, *, user_id: UUID, new_plan_code: str) -> SubscriptionRecord:
        sub = self._user_sub(user_id)
        price = self.get_price(new_plan_code)
        old = sub.plan_code
        sub.plan_code = price.plan_code
        sub.price_version = price.price_version
        sub.amount_minor = price.amount_minor
        sub.currency = price.currency
        sub.updated_at = utcnow()
        self._audit(
            str(user_id), "price_change", from_plan=old, to_plan=new_plan_code, price_version=price.price_version
        )
        return sub

    def admin_reconciliation(self) -> dict[str, Any]:
        """Minimal admin view — no PAN, minimal PII."""
        return {
            "engine": BILLING_ENGINE_VERSION,
            "subscriptions": [
                {
                    "id": str(s.id),
                    "user_id": str(s.user_id),
                    "plan_code": s.plan_code,
                    "price_version": s.price_version,
                    "status": s.status,
                    "amount_minor": s.amount_minor,
                    "dunning_attempts": s.dunning_attempts,
                    "period_end": s.current_period_end.isoformat(),
                }
                for s in self.subscriptions.values()
            ],
            "webhook_count": len(self.webhooks),
            "unprocessed_webhooks": sum(1 for w in self.webhooks.values() if not w.processed),
            "payment_attempts": len(self.attempts),
            "refunds_needs_review": sum(1 for r in self.refunds if r.status == "needs_review"),
            "audit_tail": [
                {"at": a.at.isoformat(), "actor": a.actor, "action": a.action, "detail": a.detail}
                for a in self.audit[-50:]
            ],
            "provider": self.payment.name,
            "capabilities": {
                "receipts": self.payment.capabilities().receipts,
                "refunds": self.payment.capabilities().refunds,
                "sandbox_only": self.payment.capabilities().sandbox_only,
            },
        }

    def _user_sub(self, user_id: UUID) -> SubscriptionRecord:
        sid = self.by_user.get(user_id)
        if not sid or sid not in self.subscriptions:
            raise BillingError("no_subscription", "No subscription", http_status=404)
        return self.subscriptions[sid]

    def _sub_public(self, sub: SubscriptionRecord) -> dict[str, Any]:
        return {
            "id": str(sub.id),
            "plan_code": sub.plan_code,
            "price_version": sub.price_version,
            "amount_minor": sub.amount_minor,
            "currency": sub.currency,
            "status": sub.status,
            "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
            "current_period_end": sub.current_period_end.isoformat(),
            "access_until": sub.current_period_end.isoformat(),
            "cancellation_at_period_end": sub.cancellation_at_period_end,
            "recurring_enabled": sub.recurring_enabled,
            "next_renewal_at": sub.next_renewal_at.isoformat() if sub.next_renewal_at else None,
            "has_payment_method": bool(sub.payment_method_ref),
            "dunning_attempts": sub.dunning_attempts,
        }
