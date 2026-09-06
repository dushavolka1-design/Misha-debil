"""Origin / Referer check for cookie-authenticated state changes (CSRF mitigation).

Full double-submit token: CSRF_DOUBLE_SUBMIT_NEEDS_REVIEW — tracked as blocker B-06.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class OriginCheckMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, allowed_origins: list[str]) -> None:
        super().__init__(app)
        self.allowed = {o.rstrip("/") for o in allowed_origins if o}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in SAFE_METHODS:
            return await call_next(request)
        # Webhooks use signature auth — skip Origin (providers often omit it)
        path = request.url.path
        if path.startswith("/billing/webhooks/"):
            return await call_next(request)
        # Only enforce when session cookie present
        if not request.cookies.get("dar_session"):
            return await call_next(request)
        origin = request.headers.get("origin") or ""
        referer = request.headers.get("referer") or ""
        if origin:
            if origin.rstrip("/") not in self.allowed:
                return JSONResponse(
                    status_code=403,
                    content={"code": "csrf_origin_rejected", "detail": "Origin not allowed"},
                )
        elif referer:
            try:
                parsed = urlsplit(referer)
                referer_origin = f"{parsed.scheme}://{parsed.netloc}"
            except ValueError:
                referer_origin = ""
            if referer_origin not in self.allowed:
                return JSONResponse(
                    status_code=403,
                    content={"code": "csrf_referer_rejected", "detail": "Referer not allowed"},
                )
        # Missing Origin+Referer on cookie POST: reject in production-like envs
        env = getattr(request.app.state, "csrf_strict", False)
        if env and not origin and not referer:
            return JSONResponse(
                status_code=403,
                content={"code": "csrf_missing_origin", "detail": "Origin required"},
            )
        return await call_next(request)
