from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.persistence.bootstrap import mark_analysis_dirty
from app.services.analysis.document_extract import page_count_limit_exceeded
from app.services.analysis.pipeline import AnalysisError, AnalysisPipelineService, AnalysisStatus
from app.services.jobs.queue import enqueue_job, parse_document_id, requeue_with_retry
from app.services.upload.fsm import DocumentState
from app.services.upload.lifecycle import DocumentLifecycleService, UploadError

logger = logging.getLogger(__name__)


async def handle_job_payload(
    payload: dict[str, Any],
    *,
    doc_service: DocumentLifecycleService,
    analysis_service: AnalysisPipelineService,
    redis_client,
    queue_name: str,
    max_analysis_pages: int,
    demo_mode: bool,
) -> None:
    job_type = payload.get("type")
    document_id = parse_document_id(payload)
    job_id = str(payload.get("job_id") or f"{job_type}:{document_id}")

    try:
        if job_type == "scan":
            await doc_service.run_scan_job(document_id=document_id, job_id=job_id)
            doc = doc_service.store.documents[document_id]
            if doc.state == DocumentState.CLEAN:
                await enqueue_job(
                    redis_client,
                    queue_name,
                    {"type": "process", "document_id": str(document_id), "job_id": f"process:{document_id}"},
                )
        elif job_type == "process":
            await doc_service.run_process_job(document_id=document_id, job_id=job_id)
            doc = doc_service.store.documents[document_id]
            if doc.state == DocumentState.READY:
                run = analysis_service.start_run(
                    document_id=document_id,
                    user_id=doc.user_id,
                    tenant_id=doc.tenant_id,
                    fixture_id=None,
                )
                mark_analysis_dirty()
                await enqueue_job(
                    redis_client,
                    queue_name,
                    {
                        "type": "analysis",
                        "document_id": str(document_id),
                        "run_id": str(run.id),
                        "job_id": f"analysis:{run.id}",
                    },
                )
        elif job_type == "analysis":
            run_id = UUID(str(payload["run_id"]))
            doc = doc_service.store.documents[document_id]
            if doc.state != DocumentState.READY:
                raise AnalysisError("document_not_ready", "Document must be READY", http_status=409)
            data = await doc_service.read_plaintext_for_analysis(document_id)
            if page_count_limit_exceeded(data, doc.detected_type or "pdf", max_analysis_pages):
                run = analysis_service.store.runs[run_id]
                run.status = AnalysisStatus.FAILED
                run.error_code = "page_limit_exceeded"
                mark_analysis_dirty()
                return
            fixture_id = payload.get("fixture_id") if demo_mode else None
            await analysis_service.execute(
                run_id,
                file_bytes=data,
                detected_type=doc.detected_type or "pdf",
                content_type=doc.declared_content_type,
                demo_mode=demo_mode,
                max_pages=max_analysis_pages,
                fixture_id=str(fixture_id) if fixture_id else None,
            )
            mark_analysis_dirty()
        else:
            logger.warning("unknown_job_type type=%s", job_type)
    except (UploadError, AnalysisError) as exc:
        logger.warning(
            "job_failed type=%s document_id=%s code=%s",
            job_type,
            document_id,
            getattr(exc, "code", "error"),
        )
        await requeue_with_retry(redis_client, queue_name, payload)
    except Exception:
        logger.exception("job_exception type=%s document_id=%s", job_type, document_id)
        await requeue_with_retry(redis_client, queue_name, payload)
