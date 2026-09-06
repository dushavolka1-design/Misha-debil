from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from app.services.jobs.broker import JobBroker
from app.services.jobs.runner import handle_job_payload

logger = logging.getLogger(__name__)


async def run_queue_consumer(
    *,
    redis_client: JobBroker,
    queue_name: str,
    doc_service: Any,
    analysis_service: Any,
    max_analysis_pages: int,
    demo_mode: bool,
    flush_persistence: Callable[[], None],
    stop: asyncio.Event,
) -> None:
    logger.info("queue_consumer_started queue=%s", queue_name)
    while not stop.is_set():
        try:
            payload = await redis_client.pop(queue_name, timeout=1)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("queue_blpop_error")
            await asyncio.sleep(1)
            continue
        if payload is None:
            continue
        try:
            await handle_job_payload(
                payload,
                doc_service=doc_service,
                analysis_service=analysis_service,
                redis_client=redis_client,
                queue_name=queue_name,
                max_analysis_pages=max_analysis_pages,
                demo_mode=demo_mode,
            )
            flush_persistence()
        except Exception:
            logger.exception(
                "queue_consumer_handler_error type=%s document_id=%s",
                payload.get("type"),
                payload.get("document_id"),
            )
    logger.info("queue_consumer_stopped")
