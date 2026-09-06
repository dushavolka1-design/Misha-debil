from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session

from app.models import JobQueueItem


class JobBroker(Protocol):
    async def ping(self) -> bool: ...

    async def enqueue(self, queue_name: str, payload: dict[str, Any]) -> None: ...

    async def pop(self, queue_name: str, timeout: float = 1.0) -> dict[str, Any] | None: ...

    async def requeue_with_retry(
        self,
        queue_name: str,
        payload: dict[str, Any],
        *,
        max_attempts: int = 3,
    ) -> None: ...

    async def aclose(self) -> None: ...


class RedisJobBroker:
    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    async def ping(self) -> bool:
        return bool(await self._redis.ping())

    async def enqueue(self, queue_name: str, payload: dict[str, Any]) -> None:
        safe = {k: v for k, v in payload.items() if not str(k).startswith("_")}
        await self._redis.rpush(queue_name, json.dumps(safe, default=str))

    async def pop(self, queue_name: str, timeout: float = 1.0) -> dict[str, Any] | None:
        item = await self._redis.blpop(queue_name, timeout=max(1, int(timeout)))
        if item is None:
            return None
        _, raw = item
        return json.loads(raw)

    async def requeue_with_retry(
        self,
        queue_name: str,
        payload: dict[str, Any],
        *,
        max_attempts: int = 3,
    ) -> None:
        attempt = int(payload.get("attempt", 0)) + 1
        payload = {**payload, "attempt": attempt}
        if attempt > max_attempts:
            await self._redis.rpush(f"{queue_name}:dead", json.dumps(payload, default=str))
            return
        await self.enqueue(queue_name, payload)

    async def aclose(self) -> None:
        await self._redis.aclose()


class SqliteJobBroker:
    def __init__(self, db_path: Path, queue_name: str = "dar-jobs") -> None:
        self._path = Path(db_path)
        self._queue_name = queue_name
        self._engine = create_engine("sqlite:///" + self._path.as_posix(), future=True)

    async def ping(self) -> bool:
        with Session(self._engine) as session:
            session.execute(select(JobQueueItem.id).limit(1))
        return True

    async def enqueue(self, queue_name: str, payload: dict[str, Any]) -> None:
        safe = {k: v for k, v in payload.items() if not str(k).startswith("_")}
        with Session(self._engine) as session:
            session.add(
                JobQueueItem(
                    queue_name=queue_name,
                    payload_json=json.dumps(safe, default=str),
                    status="pending",
                    attempt=int(payload.get("attempt", 0)),
                    created_at=datetime.now(UTC),
                )
            )
            session.commit()

    async def pop(self, queue_name: str, timeout: float = 1.0) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout
        while True:
            with Session(self._engine) as session:
                row = session.scalar(
                    select(JobQueueItem)
                    .where(JobQueueItem.queue_name == queue_name, JobQueueItem.status == "pending")
                    .order_by(JobQueueItem.id)
                    .limit(1)
                )
                if row is not None:
                    session.execute(update(JobQueueItem).where(JobQueueItem.id == row.id).values(status="processing"))
                    session.commit()
                    return json.loads(row.payload_json)
            if time.monotonic() >= deadline:
                return None
            import asyncio

            await asyncio.sleep(0.05)

    async def requeue_with_retry(
        self,
        queue_name: str,
        payload: dict[str, Any],
        *,
        max_attempts: int = 3,
    ) -> None:
        attempt = int(payload.get("attempt", 0)) + 1
        payload = {**payload, "attempt": attempt}
        status = "dead" if attempt > max_attempts else "pending"
        with Session(self._engine) as session:
            session.add(
                JobQueueItem(
                    queue_name=queue_name if status == "pending" else f"{queue_name}:dead",
                    payload_json=json.dumps(payload, default=str),
                    status="pending" if status == "pending" else "dead",
                    attempt=attempt,
                    created_at=datetime.now(UTC),
                )
            )
            session.commit()

    async def aclose(self) -> None:
        self._engine.dispose()
