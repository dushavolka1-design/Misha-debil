"""Real route authorization with a service spy; not installer acceptance."""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import documents
from app.routers.auth import current_user
from app.services.auth_consent import AuthConsentStore
from app.services.upload.fsm import DocumentState

DOCUMENT_ID = uuid4()
PATHS = [
    "/documents/admin/purge-expired",
    f"/documents/{DOCUMENT_ID}/jobs/scan",
    f"/documents/{DOCUMENT_ID}/jobs/process",
    f"/documents/{DOCUMENT_ID}/jobs/purge",
]


class ServiceSpy:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.document = SimpleNamespace(id=DOCUMENT_ID, state=DocumentState.READY, processed_jobs=set())
        self.store = SimpleNamespace(documents={DOCUMENT_ID: self.document})

    async def purge_expired(self) -> int:
        self.calls.append("purge")
        return 0

    async def run_scan_job(self, *, document_id: UUID, job_id: str) -> SimpleNamespace:
        self.calls.append("scan")
        return self.document

    async def run_process_job(self, *, document_id: UUID, job_id: str) -> SimpleNamespace:
        self.calls.append("process")
        return self.document

    def _require(self, document_id: UUID) -> SimpleNamespace:
        return self.document


def application(service: ServiceSpy) -> FastAPI:
    app = FastAPI()
    app.include_router(documents.router)
    app.state.auth_store = AuthConsentStore()
    app.dependency_overrides[documents.get_doc_service] = lambda: service
    return app


@pytest.mark.parametrize("path", PATHS)
def test_anonymous_cannot_run_maintenance(path: str) -> None:
    service = ServiceSpy()
    app = application(service)
    # Uses the real anonymous auth dependency, not an overridden permission check.
    with TestClient(app) as client:
        response = client.post(path, headers={"X-Job-Id": "synthetic-job", "X-Role": "admin"})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "unauthorized"
    assert service.calls == []


@pytest.mark.parametrize("role", ["user", "billing_admin", ""])
@pytest.mark.parametrize("path", PATHS)
def test_non_admin_cannot_run_maintenance(path: str, role: str) -> None:
    service = ServiceSpy()
    app = application(service)
    # Override only identity to exercise authorization independently of login.
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(id=uuid4(), role=role)
    with TestClient(app) as client:
        response = client.post(path, headers={"X-Job-Id": "synthetic-job", "X-Role": "admin"})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "forbidden"
    assert service.calls == []


@pytest.mark.parametrize("path,operation", list(zip(PATHS, ["purge", "scan", "process", "purge"], strict=True)))
def test_server_admin_reaches_maintenance_service(path: str, operation: str) -> None:
    service = ServiceSpy()
    app = application(service)
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(id=uuid4(), role="admin")
    with TestClient(app) as client:
        response = client.post(path)
    assert response.status_code == 200, response.text
    assert service.calls == [operation]
