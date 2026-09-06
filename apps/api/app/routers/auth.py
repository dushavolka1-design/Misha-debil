from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response

from app.schemas_auth import (
    ErrorBody,
    LoginRequest,
    MeResponse,
    MessageResponse,
    ProfileUpdateRequest,
    RegisterRequest,
    RegisterResponse,
    VerifyEmailRequest,
)
from app.security.rate_limit import rate_limiter
from app.services.auth_consent import (
    AcceptSpec,
    AuthConsentError,
    AuthConsentService,
    AuthConsentStore,
)
from app.settings import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "dar_session"


def get_store(request: Request) -> AuthConsentStore:
    return request.app.state.auth_store


def get_auth_service(store: AuthConsentStore = Depends(get_store)) -> AuthConsentService:
    return AuthConsentService(store)


def client_meta(request: Request) -> tuple[str | None, str | None, str]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    request_id = request.headers.get("x-request-id") or str(uuid4())
    return ip, ua, request_id


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=14 * 24 * 3600,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def current_user(
    request: Request,
    service: AuthConsentService = Depends(get_auth_service),
):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return service.user_from_session(token)


@router.post("/register", response_model=RegisterResponse, responses={400: {"model": ErrorBody}})
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    service: AuthConsentService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> RegisterResponse:
    ip, ua, request_id = client_meta(request)
    key = f"register:{ip}"
    if not rate_limiter.hit(key, limit=5, window_seconds=60):
        raise AuthConsentError("rate_limited", "Too many requests", http_status=429)
    try:
        from app.services.auth_profile import decode_avatar_jpeg

        avatar = decode_avatar_jpeg(body.avatar_data_url)
        _user, verify_token, message = service.register(
            email=str(body.email),
            password=body.password,
            display_name=body.display_name,
            avatar_jpeg=avatar,
            accepts=[AcceptSpec(c.consent_id, c.consent_version, c.content_hash) for c in body.accepts],
            locale=body.locale,
            ip=ip,
            user_agent=ua,
            request_id=request_id,
        )
    except AuthConsentError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message}) from exc

    # Send email via provider when available
    providers = getattr(request.app.state, "providers", None)
    if providers and verify_token:
        await providers.email.send(
            to=str(body.email),
            subject="Verify your email",
            body_text=f"Verification token: {verify_token}",
        )

    if settings.app_env in {"desktop", "local"} and verify_token:
        service.verify_email(verify_token)

    return RegisterResponse(
        message=message,
        verification_token_dev=verify_token
        if settings.app_env in {"local", "test", "desktop"} and verify_token
        else None,
    )


@router.post("/login", response_model=MessageResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    service: AuthConsentService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    ip, ua, _rid = client_meta(request)
    if not rate_limiter.hit(f"login:{ip}", limit=10, window_seconds=60):
        from fastapi import HTTPException

        raise HTTPException(status_code=429, detail={"code": "rate_limited", "detail": "Too many requests"})
    prev = request.cookies.get(COOKIE_NAME)
    result = service.login(
        username=body.username,
        email=body.email,
        password=body.password,
        ip=ip,
        user_agent=ua,
        previous_session_token=prev,
        require_verified=settings.app_env == "production",
    )
    # Anti-enumeration uniform message
    if not result:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_credentials", "detail": "Неверное имя или пароль"},
        )
    raw, _sess = result
    set_session_cookie(response, raw, settings)
    return MessageResponse(message="Logged in")


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    service: AuthConsentService = Depends(get_auth_service),
) -> MessageResponse:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        service.revoke_session_token(token)
    clear_session_cookie(response)
    return MessageResponse(message="Logged out")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    body: VerifyEmailRequest, service: AuthConsentService = Depends(get_auth_service)
) -> MessageResponse:
    ok = service.verify_email(body.token)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail={"code": "invalid_token", "detail": "Invalid or expired token"})
    return MessageResponse(message="Email verified")


@router.get("/me", response_model=MeResponse)
async def me(user=Depends(current_user)) -> MeResponse:
    from fastapi import HTTPException

    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    return MeResponse(
        id=user.id,
        email=user.email,
        status=user.status,
        email_verified=user.email_verified_at is not None,
        display_name=user.display_name or "",
        has_avatar=bool(user.avatar_jpeg),
    )


@router.patch("/profile", response_model=MeResponse, responses={400: {"model": ErrorBody}})
async def update_profile(
    body: ProfileUpdateRequest,
    service: AuthConsentService = Depends(get_auth_service),
    user=Depends(current_user),
) -> MeResponse:
    from fastapi import HTTPException

    from app.persistence.bootstrap import mark_auth_dirty
    from app.services.auth_profile import decode_avatar_jpeg

    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        avatar = decode_avatar_jpeg(body.avatar_data_url) if body.avatar_data_url else None
        updated = service.update_profile(
            user,
            display_name=body.display_name,
            avatar_jpeg=avatar,
            clear_avatar=body.clear_avatar,
        )
    except AuthConsentError as exc:
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message}) from exc
    mark_auth_dirty()
    return MeResponse(
        id=updated.id,
        email=updated.email,
        status=updated.status,
        email_verified=updated.email_verified_at is not None,
        display_name=updated.display_name or "",
        has_avatar=bool(updated.avatar_jpeg),
    )


@router.get("/me/avatar")
async def me_avatar(user=Depends(current_user)):
    from fastapi import HTTPException
    from fastapi.responses import Response

    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    if not user.avatar_jpeg:
        raise HTTPException(status_code=404, detail={"code": "not_found", "detail": "No avatar"})
    return Response(
        content=user.avatar_jpeg,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/sessions/revoke-others", response_model=MessageResponse)
async def revoke_others(
    request: Request,
    service: AuthConsentService = Depends(get_auth_service),
    user=Depends(current_user),
) -> MessageResponse:
    from fastapi import HTTPException

    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    token = request.cookies.get(COOKIE_NAME)
    n = service.revoke_all_sessions(user.id, except_token=token)
    return MessageResponse(message=f"Revoked {n} sessions")
