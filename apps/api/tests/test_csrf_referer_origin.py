"""Exercise the actual CSRF middleware with HTTP requests, without auth/provider mocks."""

from collections.abc import Iterator

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.security.csrf import OriginCheckMiddleware


@pytest.fixture
def client() -> Iterator[TestClient]:
    async def accepted(_request: Request) -> JSONResponse:
        return JSONResponse({"accepted": True})

    app = Starlette(routes=[Route("/change", accepted, methods=["POST"])])
    app.state.csrf_strict = True
    app.add_middleware(OriginCheckMiddleware, allowed_origins=["https://trusted.example"])
    with TestClient(app) as transport:
        transport.cookies.set("dar_session", "csrf-regression-cookie")
        yield transport


@pytest.mark.parametrize(
    "referer",
    [
        "https://trusted.example.evil.invalid/",
        "https://trusted.example@evil.invalid/",
        "https://trusted.example:8443/",
        "http://trusted.example/",
        "https://evil.invalid/?next=https://trusted.example",
        "//trusted.example/",
        "https://[invalid/",
    ],
)
def test_foreign_or_malformed_referer_is_rejected(client: TestClient, referer: str) -> None:
    response = client.post("/change", headers={"Referer": referer})
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_referer_rejected"


def test_same_origin_referer_reaches_handler(client: TestClient) -> None:
    response = client.post("/change", headers={"Referer": "https://trusted.example/profile?tab=settings"})
    assert response.status_code == 200
    assert response.json() == {"accepted": True}


def test_foreign_origin_cannot_hide_behind_trusted_referer(client: TestClient) -> None:
    response = client.post(
        "/change",
        headers={"Origin": "https://evil.invalid", "Referer": "https://trusted.example/"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_origin_rejected"


def test_same_origin_header_reaches_handler(client: TestClient) -> None:
    assert client.post("/change", headers={"Origin": "https://trusted.example"}).status_code == 200


def test_strict_cookie_request_requires_origin_information(client: TestClient) -> None:
    response = client.post("/change")
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_missing_origin"
