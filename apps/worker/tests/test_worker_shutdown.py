"""Dependency-free lifecycle tests, including a real POSIX SIGTERM."""
from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from contextlib import asynccontextmanager
from unittest.mock import patch

MAIN = Path(__file__).resolve().parents[1] / 'worker' / 'main.py'


def dependencies(lifespan):
    logging_module = types.ModuleType('dar.logging_utils')
    logging_module.configure_logging = lambda _: None
    runtime = types.ModuleType('app.services.jobs.worker_runtime')
    runtime.worker_lifespan = lifespan
    return {'dar.logging_utils': logging_module, 'app.services.jobs.worker_runtime': runtime}


def load_main():
    spec = importlib.util.spec_from_file_location('worker_shutdown_target', MAIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkerShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def test_stop_runs_lifespan_cleanup(self):
        events = []
        stop = asyncio.Event()

        @asynccontextmanager
        async def lifespan(**_):
            events.append('started')
            try:
                stop.set()
                yield None
            finally:
                events.append('cleaned')

        with patch.dict(sys.modules, dependencies(lifespan)):
            module = load_main()
            await asyncio.wait_for(module.run(stop), 2)
        self.assertEqual(events, ['started', 'cleaned'])

    async def test_cancellation_is_not_swallowed(self):
        entered = asyncio.Event()
        cleaned = asyncio.Event()

        @asynccontextmanager
        async def lifespan(**_):
            try:
                entered.set()
                yield None
            finally:
                cleaned.set()

        with patch.dict(sys.modules, dependencies(lifespan)):
            module = load_main()
            task = asyncio.create_task(module.run(asyncio.Event()))
            await asyncio.wait_for(entered.wait(), 2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(cleaned.is_set())

    async def test_startup_error_propagates(self):
        @asynccontextmanager
        async def lifespan(**_):
            raise RuntimeError('synthetic startup failure')
            yield None

        with patch.dict(sys.modules, dependencies(lifespan)):
            module = load_main()
            with self.assertRaisesRegex(RuntimeError, 'synthetic startup failure'):
                await module.run(asyncio.Event())


class WorkerSignalTests(unittest.TestCase):
    def test_real_sigterm_exits_after_cleanup(self):
        self.assertEqual(os.name, 'posix', 'Run POSIX signal acceptance on the Linux job')
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / 'ready'
            script = f'''
import runpy, sys, types
from pathlib import Path
from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(**kwargs):
    Path({str(marker)!r}).write_text('started')
    try:
        yield None
    finally:
        print('lifespan_cleanup_completed', flush=True)
logging_module = types.ModuleType('dar.logging_utils')
logging_module.configure_logging = lambda _: None
runtime = types.ModuleType('app.services.jobs.worker_runtime')
runtime.worker_lifespan = lifespan
sys.modules['dar.logging_utils'] = logging_module
sys.modules['app.services.jobs.worker_runtime'] = runtime
runpy.run_path({str(MAIN)!r}, run_name='__main__')
'''
            child = subprocess.Popen([sys.executable, '-c', script], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 5
                while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(marker.exists(), 'Worker never became ready')
                child.send_signal(signal.SIGTERM)
                stdout, stderr = child.communicate(timeout=5)
                self.assertEqual(child.returncode, 0, stderr)
                self.assertIn('lifespan_cleanup_completed', stdout)
            finally:
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=5)


if __name__ == '__main__':
    unittest.main()
