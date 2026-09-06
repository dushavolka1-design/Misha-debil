from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.deps import ProviderBundle, build_providers
from app.persistence.bootstrap import attach_persistence, flush_persistence, load_persistence, mark_auth_dirty
from app.services.analysis.pipeline import AnalysisPipelineService, AnalysisStore
from app.services.auth_consent import AuthConsentStore, seed_demo_legal
from app.services.jobs.consumer import run_queue_consumer
from app.services.upload.lifecycle import DocumentLifecycleService, DocumentStore
from app.services.upload.retention import RetentionPolicy
from app.settings import get_settings

logger = logging.getLogger(__name__)


class _WorkerState:
    def __init__(self) -> None:
        self.doc_store: DocumentStore | None = None
        self.doc_service: DocumentLifecycleService | None = None
        self.analysis_store: AnalysisStore | None = None
        self.auth_store: AuthConsentStore | None = None


@asynccontextmanager
async def worker_lifespan(*, legal_root: str) -> AsyncIterator[ProviderBundle]:
    settings = get_settings()
    bundle = build_providers(settings)
    store = AuthConsentStore()

    doc_store = DocumentStore()
    doc_service = DocumentLifecycleService(
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
    analysis_store = AnalysisStore()
    analysis_service = AnalysisPipelineService(analysis_store, ocr=bundle.ocr, llm=bundle.llm)

    state = _WorkerState()
    state.doc_store = doc_store
    state.doc_service = doc_service
    state.analysis_store = analysis_store
    state.auth_store = store

    load_persistence(state)
    seed_demo_legal(store, legal_root)
    attach_persistence(state)
    mark_auth_dirty()
    flush_persistence(state)

    stop = asyncio.Event()
    task = asyncio.create_task(
        run_queue_consumer(
            redis_client=bundle.redis,
            queue_name=settings.queue_name,
            doc_service=doc_service,
            analysis_service=analysis_service,
            max_analysis_pages=settings.max_analysis_pages,
            demo_mode=settings.demo_mode,
            flush_persistence=lambda: flush_persistence(state),
            stop=stop,
        ),
    )
    try:
        yield bundle
    finally:
        stop.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        flush_persistence(state)
        await bundle.redis.aclose()
