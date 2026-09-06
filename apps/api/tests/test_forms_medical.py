from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone, UTC
from pathlib import Path
from uuid import uuid4

import pytest
from dar.providers.fake import FakeKMSProvider, FakeMalwareScanner, InMemoryObjectStorage
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.auth_consent import (
    REQUIRED_AT_REGISTRATION,
    SPECIAL_MEDICAL,
    AcceptSpec,
    AuthConsentService,
    AuthConsentStore,
    seed_demo_legal,
)
from app.services.forms.catalog import MVP_MVD_CANDIDATE, FormCatalogService, FormError
from app.services.forms.medical import MedicalSectionService
from app.services.forms.pdf_memo import (
    FORBIDDEN_MEDICAL_ARTIFACTS,
    MEDICAL_PDF_BANNER,
    MedicalPdfError,
    assert_medical_artifact_allowed,
)
from app.services.sources.fetcher import FakeFetchScript
from app.services.sources.registry import FetchResult, SourceRegistry
from app.services.sources.url_policy import load_allowlist
from app.services.upload.lifecycle import DocumentLifecycleService, DocumentStore
from app.services.upload.retention import DEFAULT_RETENTION, MEDICAL_RETENTION

ROOT = Path(__file__).resolve().parents[3]
LEGAL = ROOT / "legal"
ALLOWLIST = str(ROOT / "sources" / "allowlist.json")


def _approve_host(reg: SourceRegistry, host_substr: str, *, act_number: str = "1", with_act: bool = True):
    reg.seed_from_allowlist()
    src = next(s for s in reg.sources.values() if host_substr in s.host)
    body = f"<html>official {src.host} form body</html>".encode()
    reg.fetch_fn = FakeFetchScript(
        {
            src.official_url: FetchResult(
                final_url=src.official_url,
                status_code=200,
                headers={"content-type": "text/html", "etag": "1"},
                body=body,
                redirect_chain=[src.official_url],
            ),
        },
    )
    snap = reg.fetch_and_parse(src.id)
    kwargs = {
        "actor": "reviewer@test",
        "comment": "approve",
        "valid_from": date(2024, 1, 1),
        "act_title": f"Act for {src.host}",
    }
    if with_act:
        kwargs["act_number"] = act_number
        kwargs["act_date"] = date(2024, 1, 1)
    reg.approve(snap.id, **kwargs)
    approved = reg.approved_snapshot(src.id)
    assert approved
    return src, approved, body


@pytest.fixture()
def registry() -> SourceRegistry:
    return SourceRegistry(allowlist=load_allowlist(ALLOWLIST))


@pytest.fixture()
def auth_store() -> AuthConsentStore:
    s = AuthConsentStore()
    seed_demo_legal(s, str(LEGAL))
    return s


@pytest.fixture()
def doc_service() -> DocumentLifecycleService:
    return DocumentLifecycleService(
        DocumentStore(),
        storage=InMemoryObjectStorage(),
        malware=FakeMalwareScanner(),
        kms=FakeKMSProvider(),
        bucket_quarantine="dar-quarantine",
        bucket_originals="dar-originals",
        bucket_derived="dar-derived",
        bucket_reports="dar-reports",
        presign_secret="test_presign_secret",
    )


@pytest.fixture()
def client(auth_store: AuthConsentStore, doc_service: DocumentLifecycleService, registry: SourceRegistry):
    app = create_app()
    with TestClient(app) as c:
        c.app.state.auth_store = auth_store
        c.app.state.doc_store = doc_service.store
        c.app.state.doc_service = doc_service
        catalog = FormCatalogService(registry)
        catalog.seed_mvp_mvd_verification()
        c.app.state.source_registry = registry
        c.app.state.form_catalog = catalog
        c.app.state.medical_section = MedicalSectionService(registry)
        yield c


def _register_login(client: TestClient, store: AuthConsentStore, email: str):
    auth = AuthConsentService(store)
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
    login = client.post("/auth/login", json={"email": email, "password": "longpassword1"})
    assert login.status_code == 200
    return user


def test_mvp_mvd_without_verified_raw_is_needs_review_not_published(registry: SourceRegistry) -> None:
    catalog = FormCatalogService(registry)
    rec = catalog.seed_mvp_mvd_verification()
    assert rec.status == "needs_review"
    assert rec.slug == MVP_MVD_CANDIDATE["slug"]
    assert catalog.list_forms(status="published") == []
    assert "needs_review" in rec.warning


def test_cannot_register_form_without_approved_source(registry: SourceRegistry) -> None:
    catalog = FormCatalogService(registry)
    registry.seed_from_allowlist()
    raw = b"not-approved-raw"
    with pytest.raises(FormError) as ei:
        catalog.register_form(
            slug="x.form",
            title="X",
            organ="МВД России",
            purpose="migration_registration",
            region="RF",
            authority="МВД",
            source_snapshot_id=uuid4(),
            raw_original=raw,
            content_sha256=hashlib.sha256(raw).hexdigest(),
            act_number="856",
            act_date=date(2020, 12, 10),
            act_title="Приказ",
            valid_from=date(2024, 1, 1),
            valid_to=None,
            reviewed_at=datetime.now(UTC),
            reviewer="editor",
        )
    assert ei.value.code == "source_not_approved"


def test_register_requires_hash_match_and_metadata(registry: SourceRegistry) -> None:
    _, snap, body = _approve_host(registry, "mvd.gov.ru", act_number="856")
    catalog = FormCatalogService(registry)
    with pytest.raises(FormError) as ei:
        catalog.register_form(
            slug="mvd.test",
            title="T",
            organ="МВД России",
            purpose="migration_registration",
            region="RF",
            authority="МВД",
            source_snapshot_id=snap.id,
            raw_original=body,
            content_sha256="0" * 64,
            act_number="856",
            act_date=date(2020, 12, 10),
            act_title="Приказ",
            valid_from=date(2024, 1, 1),
            valid_to=None,
            reviewed_at=datetime.now(UTC),
            reviewer="editor",
        )
    assert ei.value.code == "hash_mismatch"

    rec = catalog.register_form(
        slug="mvd.verified",
        title="Verified MVD form",
        organ="МВД России",
        purpose="migration_registration",
        region="RF",
        authority="МВД России",
        source_snapshot_id=snap.id,
        raw_original=body,
        content_sha256=hashlib.sha256(body).hexdigest(),
        act_number="856",
        act_date=date(2020, 12, 10),
        act_title="Приказ МВД N 856",
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewed_at=datetime.now(UTC),
        reviewer="editor@test",
    )
    assert rec.status == "published"
    card = catalog.card(rec)
    assert card["source"]["usable_as_basis"] is True
    assert card["has_raw"] is True


def test_catalog_filters_and_cards(registry: SourceRegistry) -> None:
    _, snap, body = _approve_host(registry, "mvd.gov.ru")
    catalog = FormCatalogService(registry)
    catalog.register_form(
        slug="mvd.a",
        title="A",
        organ="МВД России",
        purpose="migration_registration",
        region="77",
        authority="МВД",
        source_snapshot_id=snap.id,
        raw_original=body,
        content_sha256=hashlib.sha256(body).hexdigest(),
        act_number="1",
        act_date=date(2024, 1, 1),
        act_title="Act",
        valid_from=date(2024, 1, 1),
        valid_to=date(2030, 6, 1),
        reviewed_at=datetime.now(UTC),
        reviewer="ed",
    )
    assert catalog.list_forms(purpose="migration_registration", status="published", as_of=date(2025, 1, 1))
    assert catalog.list_forms(as_of=date(2031, 1, 1), status="published") == []


def test_forbidden_medical_artifacts_blocked_even_direct_call() -> None:
    for kind in ("certificate", "spravka", "diagnosis", "with_stamp", "with_qr", "analysis_result", "conclusion"):
        with pytest.raises(MedicalPdfError) as ei:
            assert_medical_artifact_allowed(kind)
        assert ei.value.code == "forbidden_medical_artifact"
        assert ei.value.http_status == 403


def test_medical_pdf_api_blocks_forbidden_kinds(client: TestClient, auth_store: AuthConsentStore) -> None:
    _register_login(client, auth_store, "medpdf@example.com")
    auth = AuthConsentService(auth_store)
    user = auth_store.users[auth_store.users_by_email["medpdf@example.com"]]
    med = auth_store.active_legal(SPECIAL_MEDICAL)
    assert med
    auth.accept(
        user,
        consent_id=med.consent_id,
        consent_version=med.consent_version,
        content_hash=med.content_hash,
        locale="ru-RU",
        ip="127.0.0.1",
        user_agent="test",
        request_id=str(uuid4()),
    )

    for kind in list(FORBIDDEN_MEDICAL_ARTIFACTS)[:10]:
        res = client.post("/forms/medical/pdf", json={"kind": kind, "title": "X", "body_lines": ["y"]})
        assert res.status_code == 403, kind
        assert res.json()["detail"]["code"] == "forbidden_medical_artifact"

    ok = client.post(
        "/forms/medical/pdf",
        json={"kind": "memo", "title": "Pamyatka", "body_lines": ["step 1"], "answers": {"q1": "a"}},
    )
    assert ok.status_code == 200
    assert ok.headers["content-type"].startswith("application/pdf")
    assert b"BANNER" in ok.content or b"Ne yavlyaetsya" in ok.content
    assert MEDICAL_PDF_BANNER


def test_medical_org_not_shown_outside_validity(registry: SourceRegistry) -> None:
    _, snap, _ = _approve_host(registry, "minzdrav.gov.ru")
    med = MedicalSectionService(registry)
    med.register_org(
        name="Org A",
        region_code="77",
        source_snapshot_id=snap.id,
        valid_from=date(2025, 1, 1),
        valid_to=date(2025, 12, 31),
    )
    assert med.list_orgs(region_code="77", as_of=date(2025, 6, 1))
    assert med.list_orgs(region_code="77", as_of=date(2024, 6, 1)) == []
    assert med.list_orgs(region_code="77", as_of=date(2026, 1, 2)) == []


def test_medical_procedure_rejects_non_health_source(registry: SourceRegistry) -> None:
    _, snap, _ = _approve_host(registry, "mid.ru")
    med = MedicalSectionService(registry)
    with pytest.raises(Exception) as ei:
        med.register_procedure(
            slug="p1",
            title="T",
            explanation="E",
            applicable_to="foreigners",
            deadline_text="from source: 30 days",
            source_snapshot_id=snap.id,
            checklist=["a"],
            questionnaire_fields=["name"],
        )
    assert getattr(ei.value, "code", "") == "source_not_medical_authority"


def test_abuse_report(client: TestClient) -> None:
    res = client.post(
        "/forms/abuse-reports",
        json={"target_type": "form", "target_id": MVP_MVD_CANDIDATE["slug"], "reason": "outdated", "comment": "stale"},
    )
    assert res.status_code == 200
    assert "id" in res.json()


def test_medical_upload_shorter_retention_and_role(doc_service: DocumentLifecycleService) -> None:
    uid = uuid4()
    tid = uuid4()
    doc, _ = doc_service.create_upload_intent(
        user_id=uid,
        tenant_id=tid,
        plan_code="free",
        display_filename="scan.pdf",
        content_type="application/pdf",
        size_bytes=100,
        potentially_medical=True,
    )
    assert doc.is_medical is True
    assert doc.access_role == "medical_restricted"
    assert doc.retention_expires_at is not None
    delta = doc.retention_expires_at - doc.created_at
    assert delta <= timedelta(days=MEDICAL_RETENTION.original_days + 1)
    assert MEDICAL_RETENTION.original_days < DEFAULT_RETENTION.original_days

    other = uuid4()
    with pytest.raises(Exception) as ei:
        doc_service.assert_document_access(doc, user_id=other, user_role="user")
    assert getattr(ei.value, "code", "") == "medical_access_denied"
    doc_service.assert_document_access(doc, user_id=uid, user_role="user")
    doc_service.assert_document_access(doc, user_id=other, user_role="medical_reviewer")


def test_forms_list_api_shows_needs_review_mvd(client: TestClient) -> None:
    res = client.get("/forms")
    assert res.status_code == 200
    data = res.json()
    assert any(f["slug"] == MVP_MVD_CANDIDATE["slug"] and f["status"] == "needs_review" for f in data)
    assert not any(f["slug"] == MVP_MVD_CANDIDATE["slug"] and f["status"] == "published" for f in data)
