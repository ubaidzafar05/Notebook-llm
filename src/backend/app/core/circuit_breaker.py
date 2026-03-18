from __future__ import annotations

import functools
import logging
import threading
import time
from typing import Any
from collections.abc import Callable

logger = logging.getLogger(__name__)


class CircuitBreakerError(Exception):
    """Raised when the circuit breaker is OPEN."""

    pass


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.exceptions = exceptions

        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"
        self._lock = threading.Lock()

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self._lock:
                if self.state == "OPEN":
                    if time.time() - self.last_failure_time > self.recovery_timeout:
                        logger.info("CircuitBreaker[%s] moving to HALF_OPEN", self.name)
                        self.state = "HALF_OPEN"
                    else:
                        raise CircuitBreakerError(f"Circuit {self.name} is OPEN")

            try:
                result = func(*args, **kwargs)
            except self.exceptions as exc:
                with self._lock:
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    logger.warning(
                        "CircuitBreaker[%s] recorded failure %d/%d",
                        self.name,
                        self.failure_count,
                        self.failure_threshold,
                    )

                    if self.state == "HALF_OPEN" or self.failure_count >= self.failure_threshold:
                        if self.state != "OPEN":
                            logger.error("CircuitBreaker[%s] tripped to OPEN", self.name)
                        self.state = "OPEN"
                raise exc

            with self._lock:
                if self.state == "HALF_OPEN":
                    logger.info("CircuitBreaker[%s] recovered to CLOSED", self.name)
                    self.state = "CLOSED"
                    self.failure_count = 0
                elif self.state == "CLOSED":
                    self.failure_count = 0

            return result

        return wrapper
