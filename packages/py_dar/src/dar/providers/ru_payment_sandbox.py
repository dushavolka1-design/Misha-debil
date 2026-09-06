from __future__ import annotations

"""Russian payment sandbox adapter — NO production API calls without credentials + contract.

Mimics a RU PSP (YooKassa-like) webhook/signature shape for local/test.
Production live mode requires RU_PAYMENT_SHOP_ID + RU_PAYMENT_SECRET + approved offer.
"""

import hashlib
import hmac
import json
import os
import time
from typing import Any
from uuid import UUID, uuid4

from dar.providers.ports import (
    PaymentProvider,
    PaymentSession,
    ProviderCapabilities,
    WebhookVerification,
)


class RuPaymentSandboxProvider(PaymentProvider):
    """Sandbox/stub for Russian PSP. Never hits production endpoints in this module."""

    name = "ru_payment_sandbox"

    def __init__(
        self,
        *,
        shop_id: str | None = None,
        secret: str | None = None,
        live_mode: bool = False,
        webhook_secret: str | None = None,
    ) -> None:
        self.shop_id = shop_id or os.environ.get("RU_PAYMENT_SHOP_ID", "")
        self.secret = secret or os.environ.get("RU_PAYMENT_SECRET", "")
        self.live_mode = live_mode or os.environ.get("RU_PAYMENT_LIVE", "").lower() in {"1", "true", "yes"}
        self.webhook_secret = (
            webhook_secret or os.environ.get("RU_PAYMENT_WEBHOOK_SECRET") or self.secret or "sandbox_webhook_secret"
        )
        self._intents: dict[str, dict[str, Any]] = {}
        if self.live_mode and (not self.shop_id or not self.secret):
            raise RuntimeError("ru_payment live mode requires RU_PAYMENT_SHOP_ID and RU_PAYMENT_SECRET")
        if self.live_mode:
            # Explicitly refuse until contract/credentials review — do not call production APIs
            raise RuntimeError(
                "Production RU payment API is disabled until credentials and contract are provided "
                "(BILLING_PROVIDER_NEEDS_REVIEW). Use sandbox mode only.",
            )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            receipts=False,  # fiscal receipts after legal/accounting review only
            refunds=False,  # refunds via provider after review
            recurring=True,
            sandbox_only=True,
            notes="Sandbox RU PSP adapter — no fiscal receipts; no production API",
        )

    async def create_checkout(self, *, user_id: UUID, plan_code: str) -> PaymentSession:
        return await self.create_payment_intent(
            user_id=user_id,
            plan_code=plan_code,
            amount_minor=0,
            currency="RUB",
            idempotency_key=str(uuid4()),
            description=f"checkout {plan_code}",
        )

    async def create_payment_intent(
        self,
        *,
        user_id: UUID,
        plan_code: str,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> PaymentSession:
        # Idempotent sandbox intent
        if idempotency_key in self._intents:
            prev = self._intents[idempotency_key]
            return PaymentSession(**prev["session"])
        ref = f"ru-sb-{idempotency_key[:16]}"
        session = PaymentSession(
            provider_ref=ref,
            status="pending",
            checkout_url=f"https://sandbox.payment.local/checkout/{ref}",
            amount_minor=amount_minor,
            currency=currency,
            idempotency_key=idempotency_key,
        )
        self._intents[idempotency_key] = {
            "session": {
                "provider_ref": session.provider_ref,
                "status": session.status,
                "checkout_url": session.checkout_url,
                "amount_minor": session.amount_minor,
                "currency": session.currency,
                "idempotency_key": session.idempotency_key,
            },
            "user_id": str(user_id),
            "plan_code": plan_code,
            "description": description,
            "metadata": metadata or {},
        }
        return session

    def verify_webhook(
        self,
        *,
        headers: dict[str, str],
        raw_body: bytes,
        now_ts: float | None = None,
    ) -> WebhookVerification:
        sig = headers.get("x-ru-payment-signature") or headers.get("X-Ru-Payment-Signature") or ""
        ts = headers.get("x-ru-payment-timestamp") or headers.get("X-Ru-Payment-Timestamp") or ""
        now = now_ts if now_ts is not None else time.time()
        try:
            ts_f = float(ts)
        except ValueError:
            return WebhookVerification(ok=False, reason="bad_timestamp")
        if abs(now - ts_f) > 300:
            return WebhookVerification(ok=False, reason="timestamp_skew")
        expected = hmac.new(self.webhook_secret.encode(), raw_body + b"." + ts.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return WebhookVerification(ok=False, reason="bad_signature")
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:  # noqa: BLE001
            return WebhookVerification(ok=False, reason="bad_json")
        sanitized = {k: v for k, v in payload.items() if k not in {"card_number", "cvc", "pan", "payer_email", "phone"}}
        return WebhookVerification(
            ok=True,
            event_id=str(sanitized.get("event_id") or ""),
            event_type=str(sanitized.get("event_type") or ""),
            occurred_at=str(sanitized.get("occurred_at") or ts),
            sanitized_payload=sanitized,
        )

    async def cancel_recurring(self, *, provider_subscription_ref: str) -> dict[str, Any]:
        return {"ok": True, "provider_ref": provider_subscription_ref, "status": "cancelled_sandbox"}

    async def request_refund(self, *, provider_payment_ref: str, amount_minor: int | None = None) -> dict[str, Any]:
        return {
            "ok": False,
            "reason": "fiscal_refund_requires_legal_accounting_review",
            "provider_ref": provider_payment_ref,
            "amount_minor": amount_minor,
            "receipt": None,
        }


def sign_ru_sandbox_webhook(*, secret: str, body: bytes, ts: str) -> str:
    return hmac.new(secret.encode(), body + b"." + ts.encode(), hashlib.sha256).hexdigest()
