from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from app.routers.auth import current_user, get_auth_service, get_store
from app.schemas_auth import LegalActiveItem
from app.services.auth_consent import AuthConsentService, AuthConsentStore, UserRecord

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/documents/active", response_model=list[LegalActiveItem])
async def list_active(store: AuthConsentStore = Depends(get_store)) -> list[LegalActiveItem]:
    ids = [
        "terms_of_use",
        "offer",
        "personal_data_processing",
        "privacy_policy",
        "marketing",
        "special_categories.medical",
        "cookies_notice",
        "payment_recurring",
    ]
    out: list[LegalActiveItem] = []
    for cid in ids:
        doc = store.active_legal(cid)
        if not doc:
            continue
        out.append(
            LegalActiveItem(
                id=doc.id,
                consent_id=doc.consent_id,
                consent_version=doc.consent_version,
                locale=doc.locale,
                content_hash=doc.content_hash,
                effective_at=doc.effective_at,
                body_path=doc.body_path,
            ),
        )
    return out


@router.get("/documents/{document_id}/text", response_class=PlainTextResponse)
async def document_text(document_id: str, store: AuthConsentStore = Depends(get_store)) -> str:
    from uuid import UUID

    try:
        uid = UUID(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc
    doc = store.legal.get(uid)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc.canonical_text


@router.get("/events/{event_id}/proof", response_class=PlainTextResponse)
async def event_proof(
    event_id: str,
    service: AuthConsentService = Depends(get_auth_service),
    user: UserRecord | None = Depends(current_user),
) -> str:
    from uuid import UUID

    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        eid = UUID(event_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc
    try:
        text = service.proof_text(eid)
    except Exception as exc:  # noqa: BLE001
        from app.services.auth_consent import AuthConsentError

        if isinstance(exc, AuthConsentError):
            raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc
        raise
    # Ensure event belongs to user
    for e in service.store.consent_events:
        if e.id == eid and e.subject_user_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
    return text
