from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from dar.logging_utils import configure_logging

from app.services.jobs.worker_runtime import worker_lifespan

logger = logging.getLogger(__name__)


def _legal_root() -> str:
    return str(Path(__file__).resolve().parents[3] / "legal")


async def run() -> None:
    configure_logging("INFO")
    async with worker_lifespan(legal_root=_legal_root()):
        logger.info("standalone_worker_running")
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _stop(*_: object) -> None:
        logger.info("worker_signal_stop")

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            signal.signal(sig, lambda *_a: _stop())

    try:
        loop.run_until_complete(run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
