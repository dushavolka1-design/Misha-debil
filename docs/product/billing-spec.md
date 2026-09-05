# Billing / subscription (этап 13)

## Scope

Server-owned subscription billing via `PaymentProvider` adapter. Russian PSP is exposed as `ru_payment_sandbox` only until live credentials + contract are provided. Production live API calls are intentionally disabled.

## Model

- **Plan / price version** — `PRICE_TABLE` in `apps/api/app/services/billing/service.py` (amounts in minor units). Client amounts are never trusted.
- **Subscription** — trial, active, past_due, cancelled, expired; `cancellation_at_period_end`; opaque `payment_method_ref` only.
- **Payment attempt** — idempotency key; receipt_ref only when provider capability + payload provide it (never invented).
- **Refund** — via provider capability or `needs_review`; no fiscal receipt fabrication.
- **Webhook raw event** — sanitized payload, hash, idempotency by provider event id, replay protection, timestamp skew.

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /billing/plans` | Server price table |
| `POST /billing/subscribe` | Start sub; optional recurring requires `payment_recurring` |
| `POST /billing/recurring/enable` | Separate clear action (amount, period, next charge, cancel path) |
| `POST /billing/cancel` | Cancel at period end; returns `access_until` |
| `POST /billing/payment-method/remove` | Explicit PM removal (not masked) |
| `GET /billing/me` | Subscription + payment history |
| `POST /billing/webhooks/{provider}` | Signed webhooks |
| `GET /billing/admin/reconciliation` | Minimal admin + audit |

## Production gates

- `PAYMENT_PROVIDER=ru_payment_live` / `yookassa` raises until credentials + contract review.
- Production lifespan refuses `sandbox_only` providers and requires `APPROVED_OFFER_VERSION`.
- Legal package must be approved (этап 12) independently.

## Tests

```bash
cd apps/api && py -3.14 -m pytest tests/test_billing.py -q
```

Covers: duplicate/forged/delayed/reordered webhooks, cancel/renew race, refund, price change, trial, provider outage, dunning limits, RU sandbox.
