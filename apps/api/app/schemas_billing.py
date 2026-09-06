from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class StartSubscriptionRequest(BaseModel):
    plan_code: str = Field(min_length=2, max_length=64)
    enable_recurring: bool = False
    accepted_payment_recurring: bool = False
    offer_version: str | None = None
    # Client may send amount for display check — server rejects mismatch
    client_amount_minor: int | None = None


class EnableRecurringRequest(BaseModel):
    accepted: bool
    shown_amount_minor: int
    shown_period_days: int
    shown_next_charge_at: str


class ChangePlanRequest(BaseModel):
    plan_code: str


class RefundRequest(BaseModel):
    payment_attempt_id: UUID
