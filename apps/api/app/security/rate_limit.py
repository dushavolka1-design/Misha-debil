from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    """Simple sliding-window limiter (per-process). Redis can wrap later."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Return True if allowed, False if rate-limited."""
        now = time.monotonic()
        with self._lock:
            q = self._events[key]
            cutoff = now - window_seconds
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


rate_limiter = RateLimiter()
