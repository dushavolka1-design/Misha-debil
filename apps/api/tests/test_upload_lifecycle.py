from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from dar.providers.fake import FakeKMSProvider, FakeMalwareScanner, InMemoryObjectStorage
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.auth_consent import (
    REQUIRED_AT_REGISTRATION,
    AcceptSpec,
    AuthConsentService,
    AuthConsentStore,
    seed_demo_legal,
)
from app.services.upload.filename import sanitize_display_filename
from app.services.upload.fsm import DocumentState, transition
from app.services.upload.lifecycle import DocumentLifecycleService, DocumentStore, UploadError
from app.services.upload.validation import DetectedType, harden_by_type, validate_upload

ROOT = Path(__file__).resolve().parents[3]
LEGAL = ROOT / "legal"
FIXTURES = ROOT / "tests" / "fixtures" / "upload"


@pytest.fixture()
def fixtures_built() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_fixtures",
        FIXTURES / "build_fixtures.py",
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.write_fixtures()


@pytest.fixture()
def auth_store() -> AuthConsentStore:
    s = AuthConsentStore()
    seed_demo_legal(s, str(LEGAL))
    return s


@pytest.fixture()
def doc_service() -> DocumentLifecycleService:
    store = DocumentStore()
    return DocumentLifecycleService(
        store,
        storage=InMemoryObjectStorage(),
        malware=FakeMalwareScanner(),
        kms=FakeKMSProvider(),
        bucket_quarantine="dar-quarantine",
        bucket_originals="dar-originals",
        bucket_derived="dar-derived",
        bucket_reports="dar-reports",
        presign_secret="test_presign_secret",
    )


def _register(auth: AuthConsentService, store: AuthConsentStore, email: str):
    accepts = []
    for cid in REQUIRED_AT_REGISTRATION:
        doc = store.active_legal(cid)
        assert doc
        accepts.append(AcceptSpec(doc.consent_id, doc.consent_version, doc.content_hash))
    local = "".join(ch for ch in email.split("@")[0] if ch.isalpha()) or "Пользователь"
    user, token, _ = auth.register(
        email=email,
        password="longpassword1",
        display_name=local[:1].upper() + local[1:],
        accepts=accepts,
        locale="ru-RU",
        ip="127.0.0.1",
        user_agent="test",
        request_id=str(uuid4()),
    )
    auth.verify_email(token)
    return user


@pytest.fixture()
def client(auth_store: AuthConsentStore, doc_service: DocumentLifecycleService):
    app = create_app()
    with TestClient(app) as c:
        c.app.state.auth_store = auth_store
        c.app.state.doc_store = doc_service.store
        c.app.state.doc_service = doc_service
        yield c


def test_sanitize_bidi_and_controls() -> None:
    nasty = "invoice\u202eexe.pdf\x00"
    clean = sanitize_display_filename(nasty)
    assert "\u202e" not in clean
    assert "\x00" not in clean
    assert "/" not in clean


def test_fsm_blocks_process_before_clean() -> None:
    with pytest.raises(Exception):
        transition(DocumentState.QUARANTINED, DocumentState.PROCESSING)


def test_mime_magic_mismatch(fixtures_built: None) -> None:
    data = (FIXTURES / "clean.png").read_bytes()
    res = validate_upload(
        data=data,
        declared_filename="clean.pdf",
        declared_content_type="application/pdf",
        expected_checksum=None,
    )
    assert res.ok is False
    assert res.reason in {"extension_magic_mismatch", "mime_magic_mismatch", "magic_not_recognized"}


def test_pdf_javascript_rejected(fixtures_built: None) -> None:
    data = (FIXTURES / "js.pdf").read_bytes()
    ok, code = harden_by_type(data, DetectedType.PDF)
    assert ok is False
    assert code and "pdf" in code


def test_docx_external_and_traversal(fixtures_built: None) -> None:
    ok, code = harden_by_type((FIXTURES / "external.docx").read_bytes(), DetectedType.DOCX)
    assert ok is False
    assert code == "docx_external_relationship"
    ok2, code2 = harden_by_type((FIXTURES / "traversal.docx").read_bytes(), DetectedType.DOCX)
    assert ok2 is False
    assert code2 == "docx_path_traversal"


def test_image_pixel_limit(fixtures_built: None) -> None:
    ok, code = harden_by_type((FIXTURES / "huge.png").read_bytes(), DetectedType.PNG)
    assert ok is False
    assert code in {"image_pixels_exceeded", "image_axis_exceeded"}


@pytest.mark.asyncio
async def test_pipeline_ready_and_no_download_before_clean(
    doc_service: DocumentLifecycleService,
    fixtures_built: None,
) -> None:
    user_id = uuid4()
    tenant_id = uuid4()
    data = (FIXTURES / "clean.pdf").read_bytes()
    doc, grant = doc_service.create_upload_intent(
        user_id=user_id,
        tenant_id=tenant_id,
        plan_code="free",
        display_filename="report.pdf",
        content_type="application/pdf",
        size_bytes=len(data),
    )
    # Before upload complete — not downloadable
    with pytest.raises(UploadError) as ei:
        await doc_service.download_derived(document_id=doc.id, user_id=user_id)
    assert ei.value.code in {"not_ready", "forbidden"}

    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(grant.url).query)
    doc = await doc_service.receive_bytes(
        document_id=doc.id,
        token=qs["token"][0],
        purpose=qs["purpose"][0],
        exp=int(qs["exp"][0]),
        sig=qs["sig"][0],
        data=data,
        declared_content_type="application/pdf",
    )
    assert doc.state == DocumentState.QUARANTINED
    with pytest.raises(UploadError):
        await doc_service.download_derived(document_id=doc.id, user_id=user_id)

    doc = await doc_service.run_scan_job(document_id=doc.id, job_id="scan:1")
    assert doc.state == DocumentState.CLEAN
    with pytest.raises(UploadError):
        await doc_service.download_derived(document_id=doc.id, user_id=user_id)

    doc = await doc_service.run_process_job(document_id=doc.id, job_id="process:1")
    assert doc.state == DocumentState.READY
    payload = await doc_service.download_derived(document_id=doc.id, user_id=user_id)
    assert payload.startswith(b"normalized:")


@pytest.mark.asyncio
async def test_idempotent_job_replay(doc_service: DocumentLifecycleService, fixtures_built: None) -> None:
    user_id = uuid4()
    data = (FIXTURES / "clean.pdf").read_bytes()
    doc, grant = doc_service.create_upload_intent(
        user_id=user_id,
        tenant_id=uuid4(),
        plan_code="free",
        display_filename="a.pdf",
        content_type="application/pdf",
        size_bytes=len(data),
        idempotency_key="idem-1",
    )
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(grant.url).query)
    await doc_service.receive_bytes(
        document_id=doc.id,
        token=qs["token"][0],
        purpose="put",
        exp=int(qs["exp"][0]),
        sig=qs["sig"][0],
        data=data,
        declared_content_type="application/pdf",
    )
    await doc_service.run_scan_job(document_id=doc.id, job_id="scan:x")
    await doc_service.run_scan_job(document_id=doc.id, job_id="scan:x")
    await doc_service.run_process_job(document_id=doc.id, job_id="process:x")
    d2 = await doc_service.run_process_job(document_id=doc.id, job_id="process:x")
    assert d2.state == DocumentState.READY
    # idempotent intent
    doc2, _ = doc_service.create_upload_intent(
        user_id=user_id,
        tenant_id=uuid4(),
        plan_code="free",
        display_filename="a.pdf",
        content_type="application/pdf",
        size_bytes=len(data),
        idempotency_key="idem-1",
    )
    assert doc2.id == doc.id


@pytest.mark.asyncio
async def test_infected_eicar(doc_service: DocumentLifecycleService, fixtures_built: None) -> None:
    data = (FIXTURES / "eicar.pdf").read_bytes()
    doc, grant = doc_service.create_upload_intent(
        user_id=uuid4(),
        tenant_id=uuid4(),
        plan_code="free",
        display_filename="eicar.pdf",
        content_type="application/pdf",
        size_bytes=len(data),
    )
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(grant.url).query)
    await doc_service.receive_bytes(
        document_id=doc.id,
        token=qs["token"][0],
        purpose="put",
        exp=int(qs["exp"][0]),
        sig=qs["sig"][0],
        data=data,
        declared_content_type="application/pdf",
    )
    doc = await doc_service.run_scan_job(document_id=doc.id, job_id="scan:e")
    assert doc.state == DocumentState.INFECTED
    with pytest.raises(UploadError):
        await doc_service.run_process_job(document_id=doc.id, job_id="process:e")


@pytest.mark.asyncio
async def test_idor_and_delete_erasure(doc_service: DocumentLifecycleService, fixtures_built: None) -> None:
    owner = uuid4()
    other = uuid4()
    data = (FIXTURES / "clean.pdf").read_bytes()
    doc, grant = doc_service.create_upload_intent(
        user_id=owner,
        tenant_id=uuid4(),
        plan_code="free",
        display_filename="own.pdf",
        content_type="application/pdf",
        size_bytes=len(data),
    )
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(grant.url).query)
    await doc_service.receive_bytes(
        document_id=doc.id,
        token=qs["token"][0],
        purpose="put",
        exp=int(qs["exp"][0]),
        sig=qs["sig"][0],
        data=data,
        declared_content_type="application/pdf",
    )
    await doc_service.run_scan_job(document_id=doc.id, job_id="s")
    await doc_service.run_process_job(document_id=doc.id, job_id="p")
    with pytest.raises(UploadError) as ei:
        await doc_service.download_derived(document_id=doc.id, user_id=other)
    assert ei.value.http_status == 404

    await doc_service.delete_document(document_id=doc.id, user_id=owner)
    proof = doc_service.verify_erasure(doc.id)
    assert proof["state"] == "DELETED"
    assert proof["cache_cleared"] is True
    assert all(b["erased_at"] for b in proof["blobs"])
    with pytest.raises(UploadError):
        await doc_service.download_derived(document_id=doc.id, user_id=owner)


@pytest.mark.asyncio
async def test_export_excludes_other_users_and_secrets(
    doc_service: DocumentLifecycleService,
    fixtures_built: None,
) -> None:
    u1, u2 = uuid4(), uuid4()
    data = (FIXTURES / "clean.pdf").read_bytes()
    for uid in (u1, u2):
        doc, grant = doc_service.create_upload_intent(
            user_id=uid,
            tenant_id=uuid4(),
            plan_code="free",
            display_filename="x.pdf",
            content_type="application/pdf",
            size_bytes=len(data),
        )
        from urllib.parse import parse_qs, urlparse

        qs = parse_qs(urlparse(grant.url).query)
        await doc_service.receive_bytes(
            document_id=doc.id,
            token=qs["token"][0],
            purpose="put",
            exp=int(qs["exp"][0]),
            sig=qs["sig"][0],
            data=data,
            declared_content_type="application/pdf",
        )
    exported = doc_service.export_user_data(user_id=u1)
    assert all(d["id"] for d in exported["documents"])
    assert "risk_score" not in str(exported)
    assert "dek" not in str(exported).lower()
    assert len(exported["documents"]) == 1


def test_api_upload_requires_auth(client: TestClient) -> None:
    res = client.post(
        "/documents/upload-intent",
        json={
            "display_filename": "a.pdf",
            "content_type": "application/pdf",
            "size_bytes": 100,
        },
    )
    assert res.status_code == 401


def test_api_happy_path_and_idor(
    client: TestClient,
    auth_store: AuthConsentStore,
    fixtures_built: None,
) -> None:
    auth = AuthConsentService(auth_store)
    user = _register(auth, auth_store, "uploader@example.com")
    other = _register(auth, auth_store, "other@example.com")
    raw, _ = auth.login(email=user.email, password="longpassword1", ip="1.1.1.1", user_agent="t")
    client.cookies.set("dar_session", raw)

    data = (FIXTURES / "clean.pdf").read_bytes()
    intent = client.post(
        "/documents/upload-intent",
        json={
            "display_filename": "contract.pdf",
            "content_type": "application/pdf",
            "size_bytes": len(data),
            "idempotency_key": "k1",
        },
    )
    assert intent.status_code == 200, intent.text
    body = intent.json()
    upload_url = body["upload_url"]
    put = client.put(upload_url, content=data, headers={"Content-Type": "application/pdf"})
    assert put.status_code == 200
    assert put.json()["state"] == "READY"
    doc_id = body["document_id"]

    # IDOR: other user
    client.cookies.clear()
    raw2, _ = auth.login(email=other.email, password="longpassword1", ip="1.1.1.1", user_agent="t")
    client.cookies.set("dar_session", raw2)
    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert client.get(f"/documents/{doc_id}/download").status_code == 404


@pytest.mark.asyncio
async def test_presign_single_use(doc_service: DocumentLifecycleService, fixtures_built: None) -> None:
    from urllib.parse import parse_qs, urlparse

    data = (FIXTURES / "clean.pdf").read_bytes()
    doc, grant = doc_service.create_upload_intent(
        user_id=uuid4(),
        tenant_id=uuid4(),
        plan_code="free",
        display_filename="a.pdf",
        content_type="application/pdf",
        size_bytes=len(data),
    )
    qs = parse_qs(urlparse(grant.url).query)
    await doc_service.receive_bytes(
        document_id=doc.id,
        token=qs["token"][0],
        purpose="put",
        exp=int(qs["exp"][0]),
        sig=qs["sig"][0],
        data=data,
        declared_content_type="application/pdf",
    )
    with pytest.raises(UploadError) as ei:
        await doc_service.receive_bytes(
            document_id=doc.id,
            token=qs["token"][0],
            purpose="put",
            exp=int(qs["exp"][0]),
            sig=qs["sig"][0],
            data=data,
            declared_content_type="application/pdf",
        )
    assert ei.value.code == "presign_replay"
