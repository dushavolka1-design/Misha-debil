from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dar.logging_utils import configure_logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.deps import ProviderBundle, build_providers
from app.persistence.bootstrap import (
    attach_persistence,
    flush_persistence,
    load_persistence,
    mark_auth_dirty,
    mark_blob_dirty,
)
from app.persistence.demo_seed import ensure_demo_account
from app.persistence.middleware import PersistenceFlushMiddleware
from app.routers import (
    analysis,
    auth,
    billing,
    documents,
    entry,
    form_fill,
    forms,
    health,
    legal,
    privacy,
    reports,
    sources,
)
from app.services.analysis.pipeline import AnalysisPipelineService, AnalysisStore
from app.services.auth_consent import AuthConsentStore, seed_demo_legal
from app.services.billing.service import BillingService
from app.services.entry.engine import EntryWizardService
from app.services.forms.catalog import FormCatalogService
from app.services.forms.fill.service import FormFillService
from app.services.forms.medical import MedicalSectionService
from app.services.jobs.consumer import run_queue_consumer
from app.services.rules.feedback import FeedbackStore
from app.services.sources.fetcher import guarded_httpx_fetch
from app.services.sources.registry import SourceRegistry
from app.services.upload.lifecycle import DocumentLifecycleService, DocumentStore
from app.services.upload.retention import RetentionPolicy
from app.services.upload.safe_logging import DocumentSafeFilter
from app.settings import get_settings


def _legal_root() -> Path:
    # apps/api/app/main.py -> repo root
    return Path(__file__).resolve().parents[3] / "legal"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.app_env == "desktop" and settings.data_dir:
        from app.desktop_boot import migrate_sqlite

        migrate_sqlite(Path(settings.data_dir))
    configure_logging(settings.log_level)
    logging.getLogger().addFilter(DocumentSafeFilter())
    bundle = build_providers(settings)
    app.state.providers = bundle

    store = AuthConsentStore()
    app.state.auth_store = store

    doc_store = DocumentStore()
    app.state.doc_store = doc_store
    app.state.doc_service = DocumentLifecycleService(
        doc_store,
        storage=bundle.storage,
        malware=bundle.malware,
        kms=bundle.kms,
        bucket_quarantine=settings.s3_bucket_quarantine,
        bucket_originals=settings.s3_bucket_originals,
        bucket_derived=settings.s3_bucket_derived,
        bucket_reports=settings.s3_bucket_reports,
        retention=RetentionPolicy(
            original_days=settings.retention_originals_days,
            normalized_render_days=settings.retention_derived_days,
            extracted_text_days=settings.retention_derived_days,
            report_days=settings.retention_reports_days,
            audit_days=settings.retention_audit_days,
        ),
        presign_secret=settings.session_secret,
        sandbox_cpu_seconds=settings.sandbox_cpu_seconds,
        sandbox_memory_hint_mb=settings.sandbox_memory_mb,
    )
    app.state.doc_service.medical_retention = RetentionPolicy(
        original_days=settings.retention_medical_originals_days,
        normalized_render_days=settings.retention_medical_derived_days,
        extracted_text_days=settings.retention_medical_derived_days,
        report_days=max(14, settings.retention_medical_derived_days),
        audit_days=settings.retention_audit_days,
    )

    analysis_store = AnalysisStore()
    app.state.analysis_store = analysis_store
    app.state.analysis_service = AnalysisPipelineService(
        analysis_store,
        ocr=bundle.ocr,
        llm=bundle.llm,
    )
    app.state.feedback_store = FeedbackStore()
    source_registry = SourceRegistry(fetch_fn=guarded_httpx_fetch)
    app.state.source_registry = source_registry
    app.state.entry_wizard = EntryWizardService(source_registry)
    form_catalog = FormCatalogService(source_registry)
    app.state.form_catalog = form_catalog
    app.state.medical_section = MedicalSectionService(source_registry)
    form_fill = FormFillService(source_registry, catalog=form_catalog)
    app.state.form_fill = form_fill

    billing_svc = BillingService(bundle.payment, email=bundle.email)
    # Production: live credentials + approved offer version required before real charges
    if settings.app_env == "production":
        caps = bundle.payment.capabilities()
        if caps.sandbox_only:
            raise RuntimeError(
                "Production billing requires a live PaymentProvider with credentials and contract "
                "(sandbox_only providers are forbidden)",
            )
        billing_svc.require_approved_offer = True
        billing_svc.approved_offer_version = settings.approved_offer_version
        if not billing_svc.approved_offer_version:
            raise RuntimeError("APPROVED_OFFER_VERSION required in production for billing")
    app.state.billing = billing_svc
    app.state.csrf_strict = settings.app_env == "production"

    load_persistence(app.state)
    seed_demo_legal(store, str(_legal_root()))
    if not source_registry.sources:
        source_registry.seed_from_allowlist()
        mark_blob_dirty("sources")
    if getattr(app.state, "catalog_persistence_error", None):
        logging.getLogger(__name__).error(
            "Catalog persistence failed: %s",
            app.state.catalog_persistence_error,
        )
    else:
        if not form_catalog.iter_records():
            from app.services.forms.catalog_seed import seed_prompt6_catalog

            seed_prompt6_catalog(form_catalog)
        else:
            from app.services.forms.catalog_seed import ensure_prompt6_catalog

            ensure_prompt6_catalog(form_catalog)
        app.state.catalog_ok = form_catalog.typed_catalog_ok()
    attach_persistence(app.state)
    mark_auth_dirty()
    ensure_demo_account(store)
    from app.services.forms.catalog_seed import link_fill_version
    from app.services.forms.official_intake import disarm_unofficial_generation, record_arrival_editorial_intake

    disarm_unofficial_generation(form_catalog, form_fill)
    record_arrival_editorial_intake(form_catalog)
    medical_fid = form_catalog.by_slug.get("medical.visit.memo")
    try:
        if medical_fid:
            ver = form_fill.seed_medical_memo_published(catalog_form_id=medical_fid)
            link_fill_version(form_catalog, slug="medical.visit.memo", fill_version_id=ver.id)
    except FileNotFoundError as exc:
        logging.getLogger(__name__).error(
            "Medical memo template not seeded — bundled font missing or invalid: %s",
            exc,
        )
    from app.services.forms.official_form_acts import apply_official_act_metadata, try_fetch_official_acts

    apply_official_act_metadata(form_catalog)
    try:
        form_fill.seed_government_worksheets(form_catalog)
    except FileNotFoundError as exc:
        logging.getLogger(__name__).error("Worksheets not seeded — bundled font missing: %s", exc)
    if os.environ.get("DOCLY_FETCH_OFFICIAL_ACTS", "").lower() in {"1", "true", "yes"}:
        try:
            try_fetch_official_acts(source_registry, form_catalog)
        except Exception:
            logging.getLogger(__name__).exception("Official act fetch bootstrap failed")
    app.state.flush_persistence = lambda: flush_persistence(app.state)
    flush_persistence(app.state)

    def _bundle() -> ProviderBundle:
        return bundle

    app.dependency_overrides[health.get_bundle] = _bundle

    queue_stop = asyncio.Event()
    queue_task = asyncio.create_task(
        run_queue_consumer(
            redis_client=bundle.queue,
            queue_name=settings.queue_name,
            doc_service=app.state.doc_service,
            analysis_service=app.state.analysis_service,
            max_analysis_pages=settings.max_analysis_pages,
            demo_mode=settings.demo_mode,
            flush_persistence=app.state.flush_persistence,
            stop=queue_stop,
        ),
    )
    yield
    queue_stop.set()
    queue_task.cancel()
    try:
        await queue_task
    except asyncio.CancelledError:
        pass
    flush_persistence(app.state)
    await bundle.queue.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    # Local: browser may use localhost or 127.0.0.1 — allow both for CORS/CSRF
    allowed_origins = {settings.web_origin.rstrip("/")}
    for origin in list(allowed_origins):
        if "://localhost" in origin:
            allowed_origins.add(origin.replace("://localhost", "://127.0.0.1"))
        if "://127.0.0.1" in origin:
            allowed_origins.add(origin.replace("://127.0.0.1", "://localhost"))
    origin_list = sorted(allowed_origins)

    app = FastAPI(
        title="Docly API",
        version="0.11.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id", "X-Job-Id", "Idempotency-Key"],
    )
    from app.security.csrf import OriginCheckMiddleware

    app.add_middleware(PersistenceFlushMiddleware)
    app.add_middleware(OriginCheckMiddleware, allowed_origins=origin_list)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(legal.router)
    app.include_router(privacy.router)
    app.include_router(documents.router)
    app.include_router(analysis.router)
    app.include_router(reports.router)
    app.include_router(sources.router)
    app.include_router(entry.router)
    app.include_router(forms.router)
    app.include_router(form_fill.router)
    app.include_router(billing.router)
    return app


app = create_app()
