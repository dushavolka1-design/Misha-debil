from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.routers.auth import current_user, get_auth_service
from app.schemas_billing import (
    ChangePlanRequest,
    EnableRecurringRequest,
    RefundRequest,
    StartSubscriptionRequest,
)
from app.services.auth_consent import AuthConsentError, AuthConsentService
from app.services.billing.service import BillingError, BillingService

router = APIRouter(prefix="/billing", tags=["billing"])


def get_billing(request: Request) -> BillingService:
    return request.app.state.billing


def _user_or_401(user):
    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    return user


def _billing_http(exc: BillingError) -> None:
    raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message})


def _consent_http(exc: AuthConsentError) -> None:
    raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message})


@router.get("/plans")
async def list_plans(service: BillingService = Depends(get_billing)) -> list[dict]:
    return service.list_plans()


@router.get("/me")
async def my_billing(service: BillingService = Depends(get_billing), user=Depends(current_user)) -> dict:
    user = _user_or_401(user)
    return service.history(user_id=user.id)


@router.post("/subscribe")
async def subscribe(
    body: StartSubscriptionRequest,
    service: BillingService = Depends(get_billing),
    auth: AuthConsentService = Depends(get_auth_service),
    user=Depends(current_user),
) -> dict:
    user = _user_or_401(user)
    try:
        auth.assert_feature_allowed(user, "product_use")
    except AuthConsentError as exc:
        _consent_http(exc)
    if body.enable_recurring or body.accepted_payment_recurring:
        try:
            auth.assert_feature_allowed(user, "payment_subscribe")
        except AuthConsentError as exc:
            _consent_http(exc)
    try:
        sub, attempt, checkout = await service.start_subscription(
            user_id=user.id,
            tenant_id=user.tenant_id,
            plan_code=body.plan_code,
            enable_recurring=body.enable_recurring,
            accepted_payment_recurring=body.accepted_payment_recurring,
            offer_version=body.offer_version,
            client_amount_minor=body.client_amount_minor,
        )
    except BillingError as exc:
        _billing_http(exc)
        raise
    return {
        "subscription": service._sub_public(sub),
        "attempt_id": str(attempt.id) if attempt else None,
        "checkout": checkout,
    }


@router.post("/recurring/enable")
async def enable_recurring(
    body: EnableRecurringRequest,
    service: BillingService = Depends(get_billing),
    auth: AuthConsentService = Depends(get_auth_service),
    user=Depends(current_user),
) -> dict:
    user = _user_or_401(user)
    try:
        auth.assert_feature_allowed(user, "payment_subscribe")
    except AuthConsentError as exc:
        _consent_http(exc)
    try:
        sub = service.enable_recurring_explicit(
            user_id=user.id,
            accepted=body.accepted,
            shown_amount_minor=body.shown_amount_minor,
            shown_period_days=body.shown_period_days,
            shown_next_charge_at=body.shown_next_charge_at,
        )
    except BillingError as exc:
        _billing_http(exc)
        raise
    return {
        "subscription": service._sub_public(sub),
        "amount_minor": sub.amount_minor,
        "period_days": service.get_price(sub.plan_code).period_days,
        "next_charge_at": sub.next_renewal_at.isoformat() if sub.next_renewal_at else None,
        "cancel_path": "/app/billing",
    }


@router.post("/cancel")
async def cancel(service: BillingService = Depends(get_billing), user=Depends(current_user)) -> dict:
    user = _user_or_401(user)
    try:
        sub = service.cancel_at_period_end(user_id=user.id)
    except BillingError as exc:
        _billing_http(exc)
        raise
    return {
        "subscription": service._sub_public(sub),
        "message": "Автопродление отключено. Доступ сохраняется до конца оплаченного периода.",
        "access_until": sub.current_period_end.isoformat(),
    }


@router.post("/payment-method/remove")
async def remove_pm(service: BillingService = Depends(get_billing), user=Depends(current_user)) -> dict:
    user = _user_or_401(user)
    try:
        sub = service.remove_payment_method(user_id=user.id)
    except BillingError as exc:
        _billing_http(exc)
        raise
    return {
        "subscription": service._sub_public(sub),
        "message": "Способ оплаты удалён. Автопродление отключено.",
    }


@router.post("/plan")
async def change_plan(
    body: ChangePlanRequest,
    service: BillingService = Depends(get_billing),
    user=Depends(current_user),
) -> dict:
    user = _user_or_401(user)
    try:
        sub = service.change_plan(user_id=user.id, new_plan_code=body.plan_code)
    except BillingError as exc:
        _billing_http(exc)
        raise
    return service._sub_public(sub)


@router.post("/refunds")
async def refund(
    body: RefundRequest,
    service: BillingService = Depends(get_billing),
    user=Depends(current_user),
) -> dict:
    user = _user_or_401(user)
    try:
        rec = await service.request_refund(user_id=user.id, payment_attempt_id=body.payment_attempt_id)
    except BillingError as exc:
        _billing_http(exc)
        raise
    return {
        "id": str(rec.id),
        "status": rec.status,
        "reason": rec.reason,
        "receipt": None,
    }


@router.post("/webhooks/{provider}")
async def webhook(
    provider: str,
    request: Request,
    service: BillingService = Depends(get_billing),
) -> JSONResponse:
    if provider not in {service.payment.name, "fake_payment", "ru_payment_sandbox"}:
        return JSONResponse(status_code=404, content={"code": "unknown_provider"})
    raw = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    try:
        result = await service.handle_webhook(headers=headers, raw_body=raw)
    except BillingError as exc:
        return JSONResponse(status_code=exc.http_status, content={"code": exc.code, "detail": exc.message})
    return JSONResponse(content=result)


@router.post("/admin/process-renewals")
async def admin_process_renewals(
    service: BillingService = Depends(get_billing),
    user=Depends(current_user),
) -> dict:
    user = _user_or_401(user)
    if getattr(user, "role", "user") not in {"admin", "billing_admin"}:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "detail": "Admin only"})
    results = await service.process_renewals()
    return {"results": results}


@router.get("/admin/reconciliation")
async def admin_reconciliation(
    service: BillingService = Depends(get_billing),
    user=Depends(current_user),
) -> dict:
    user = _user_or_401(user)
    if getattr(user, "role", "user") not in {"admin", "billing_admin"}:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "detail": "Admin only"})
    return service.admin_reconciliation()
