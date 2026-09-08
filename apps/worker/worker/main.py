from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

logger = logging.getLogger(__name__)


def _legal_root() -> str:
    return str(Path(__file__).resolve().parents[3] / "legal")


async def run(stop: asyncio.Event) -> None:
    from app.services.jobs.worker_runtime import worker_lifespan
    from dar.logging_utils import configure_logging

    configure_logging("INFO")
    async with worker_lifespan(legal_root=_legal_root()):
        logger.info("standalone_worker_running")
        await stop.wait()
    logger.info("standalone_worker_stopped")


async def _run_with_signals() -> None:
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    previous_handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    installed: list[tuple[signal.Signals, bool]] = []

    def request_stop() -> None:
        if not stop.is_set():
            logger.info("worker_signal_stop")
            stop.set()

    def fallback_handler(_signum: int, _frame: object) -> None:
        loop.call_soon_threadsafe(request_stop)

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            if previous_handlers[sig] is None:
                raise RuntimeError("Cannot safely restore the existing signal handler")
            try:
                loop.add_signal_handler(sig, request_stop)
                installed.append((sig, True))
            except NotImplementedError:
                signal.signal(sig, fallback_handler)
                installed.append((sig, False))
        await run(stop)
    finally:
        for sig, uses_loop in reversed(installed):
            if uses_loop:
                loop.remove_signal_handler(sig)
            previous = previous_handlers[sig]
            if previous is not None:
                signal.signal(sig, previous)


def main() -> None:
    # Finalize asynchronous generators and close the loop; do not hide errors.
    asyncio.run(_run_with_signals())


if __name__ == "__main__":
    main()
