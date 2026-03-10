import time

import pytest

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerError


def test_circuit_breaker_opens_after_failures() -> None:
    breaker_calls = {"count": 0}

    @CircuitBreaker(name="test_api", failure_threshold=3, recovery_timeout=0.2)
    def failing_api() -> str:
        breaker_calls["count"] += 1
        raise ValueError("API Offline")

    for _ in range(3):
        with pytest.raises(ValueError, match="API Offline"):
            failing_api()

    assert breaker_calls["count"] == 3

    # The 4th call should fail instantly with CircuitBreakerError 
    # without incrementing the mock call count
    with pytest.raises(CircuitBreakerError):
        failing_api()

    assert breaker_calls["count"] == 3

    # Wait for recovery timeout
    time.sleep(0.3)

    # 5th call should be allowed through (Half-Open)
    with pytest.raises(ValueError, match="API Offline"):
        failing_api()

    assert breaker_calls["count"] == 4
