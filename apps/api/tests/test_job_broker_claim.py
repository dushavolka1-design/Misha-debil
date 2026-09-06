"""Real SQLite claim races; synchronization never mocks database results."""

from __future__ import annotations

import asyncio
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import Select, create_engine, select
from sqlalchemy.orm import Session

from app.models import Base, JobQueueItem
from app.services.jobs.broker import SqliteJobBroker, _decode_payload


class JobPayloadTests(unittest.TestCase):
    def test_object_payload_preserves_nested_values(self) -> None:
        self.assertEqual(_decode_payload('{"id":"synthetic","nested":[true,null,3]}'),
                         {"id": "synthetic", "nested": [True, None, 3]})

    def test_non_objects_fail_without_echoing_payload(self) -> None:
        for raw in ['null', '[]', 'false', '3', '"synthetic-private-text"']:
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, '^Job payload must be a JSON object$'):
                    _decode_payload(raw)


class SqliteClaimTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'queue.db'
        self.engine = create_engine('sqlite:///' + self.path.as_posix())
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine, tables=[JobQueueItem.__table__])
        self.broker = SqliteJobBroker(self.path)
        self.addCleanup(self.broker._engine.dispose)

    def test_two_consumers_cannot_claim_same_row(self) -> None:
        asyncio.run(self.broker.enqueue('test', {'id': 'synthetic-job'}))
        barrier = threading.Barrier(2)
        original_scalar = Session.scalar

        def synchronized_scalar(session, statement, *args, **kwargs):
            result = original_scalar(session, statement, *args, **kwargs)
            if isinstance(statement, Select):
                # Both consumers really read the same pending row before either update.
                barrier.wait(timeout=10)
            return result

        def consume():
            return asyncio.run(self.broker.pop('test', wait_seconds=0))

        with patch.object(Session, 'scalar', synchronized_scalar):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(consume), pool.submit(consume)]
                results = [future.result(timeout=15) for future in futures]
        self.assertEqual(results.count({'id': 'synthetic-job'}), 1)
        self.assertEqual(results.count(None), 1)
        with Session(self.engine) as session:
            self.assertEqual(session.scalars(select(JobQueueItem.status)).all(), ['processing'])

    def test_invalid_payload_does_not_claim_row(self) -> None:
        with Session(self.engine) as session:
            session.add(JobQueueItem(queue_name='test', payload_json='[]', status='pending', attempt=0))
            session.commit()
        with self.assertRaisesRegex(ValueError, 'JSON object'):
            asyncio.run(self.broker.pop('test', wait_seconds=0))
        with Session(self.engine) as session:
            self.assertEqual(session.scalars(select(JobQueueItem.status)).all(), ['pending'])

    def test_queue_isolation_and_empty_poll(self) -> None:
        asyncio.run(self.broker.enqueue('other', {'id': 'synthetic-job'}))
        self.assertIsNone(asyncio.run(self.broker.pop('test', wait_seconds=0)))
        self.assertEqual(asyncio.run(self.broker.pop('other', wait_seconds=0)), {'id': 'synthetic-job'})
        self.assertIsNone(asyncio.run(self.broker.pop('other', wait_seconds=0)))


if __name__ == '__main__':
    unittest.main()
