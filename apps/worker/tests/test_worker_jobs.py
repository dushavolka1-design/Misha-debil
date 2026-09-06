from __future__ import annotations

import pytest

from worker.main import handle_job


@pytest.mark.asyncio
async def test_worker_job_idempotent_handler() -> None:
    calls: list[str] = []

    async def handler(payload: dict) -> None:
        calls.append(payload["job_id"])

    payload = {"type": "scan", "document_id": "d1", "job_id": "j1", "_handler": handler}
    await handle_job(payload)
    await handle_job(payload)
    # Worker itself does not dedupe — service layer does; handler invoked twice is OK
    assert calls == ["j1", "j1"]
