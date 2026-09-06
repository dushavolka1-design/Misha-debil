from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.services.jobs.broker import JobBroker

logger = logging.getLogger(__name__)

DEAD_LETTER_SUFFIX = ":dead"


async def enqueue_job(client: JobBroker, queue_name: str, payload: dict[str, Any]) -> None:
    await client.enqueue(queue_name, payload)


async def requeue_with_retry(
    client: JobBroker,
    queue_name: str,
    payload: dict[str, Any],
    *,
    max_attempts: int = 3,
) -> None:
    await client.requeue_with_retry(queue_name, payload, max_attempts=max_attempts)


def parse_document_id(payload: dict[str, Any]) -> UUID:
    return UUID(str(payload["document_id"]))
