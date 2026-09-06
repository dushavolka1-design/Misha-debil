from __future__ import annotations

import time

import pytest

from app.security.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState
from app.security.rate_limit import RateLimiter


def test_backpressure_rate_limit() -> None:
    rl = RateLimiter()
    key = "queue:worker"
    allowed = sum(1 for _ in range(20) if rl.hit(key, limit=5, window_seconds=60))
    assert allowed == 5


def test_circuit_breaker_half_open_recovery() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout_seconds=0.05, name="ocr")
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        cb.before_call()
    time.sleep(0.06)
    assert cb.state == CircuitState.HALF_OPEN
    cb.before_call()
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_provider_outage_degraded_mode() -> None:
    import asyncio
    from uuid import uuid4

    from dar.providers.fake import FakePaymentProvider

    p = FakePaymentProvider()
    p.outage = True

    async def boom() -> None:
        with pytest.raises(RuntimeError, match="provider_outage"):
            await p.create_payment_intent(
                user_id=uuid4(),
                plan_code="pro",
                amount_minor=100,
                currency="RUB",
                idempotency_key="x",
                description="d",
            )

    asyncio.run(boom())
