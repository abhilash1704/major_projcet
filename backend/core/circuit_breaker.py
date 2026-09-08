"""
circuit_breaker.py — Circuit Breaker Pattern for External Services

Protects RouteFlow from cascading failures when external providers
(e.g., TomTom, HERE, OpenRouteService, Nominatim) experience outages or timeouts.

States:
  - CLOSED: Normal operation. Requests flow through. Consecutive failures are counted.
  - OPEN: Failure threshold exceeded. Requests are blocked immediately and return
          UNAVAILABLE without making external network calls.
  - HALF_OPEN: Cooldown period elapsed. A probe request is permitted to test service health.
"""
import time
import threading
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger("routeflow.circuit_breaker")


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""
    def __init__(self, service_name: str, retry_after: float):
        self.service_name = service_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker for service '{service_name}' is OPEN. Retry after {retry_after:.1f}s."
        )


class CircuitBreaker:
    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        half_open_max_trials: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_trials = half_open_max_trials

        self._state = self.STATE_CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_trials = 0
        self._lock = threading.RLock()

    @property
    def state(self) -> str:
        with self._lock:
            self._evaluate_state()
            return self._state

    def _evaluate_state(self) -> None:
        """Transitions from OPEN to HALF_OPEN if recovery_timeout has elapsed."""
        if self._state == self.STATE_OPEN and self._last_failure_time:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                logger.info(
                    "[CircuitBreaker:%s] Recovery timeout reached (%.1fs >= %.1fs). Transitioning OPEN -> HALF_OPEN.",
                    self.name, elapsed, self.recovery_timeout
                )
                self._state = self.STATE_HALF_OPEN
                self._half_open_trials = 0

    def allow_request(self) -> bool:
        """Returns True if a request is permitted to execute, False if blocked."""
        with self._lock:
            self._evaluate_state()
            if self._state == self.STATE_CLOSED:
                return True
            elif self._state == self.STATE_HALF_OPEN:
                if self._half_open_trials < self.half_open_max_trials:
                    self._half_open_trials += 1
                    return True
                return False
            else:  # STATE_OPEN
                return False

    def record_success(self) -> None:
        """Records a successful call, resetting failure counts and closing the circuit."""
        with self._lock:
            if self._state != self.STATE_CLOSED:
                logger.info(
                    "[CircuitBreaker:%s] Probe request SUCCEEDED. Resetting state %s -> CLOSED.",
                    self.name, self._state
                )
            self._state = self.STATE_CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self._half_open_trials = 0

    def record_failure(self, exc: Optional[Exception] = None) -> None:
        """Records a failure. Tripping the threshold moves the circuit to OPEN."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            logger.warning(
                "[CircuitBreaker:%s] Failure recorded (%d/%d): %s",
                self.name, self._failure_count, self.failure_threshold, exc
            )

            if self._state == self.STATE_HALF_OPEN:
                logger.warning(
                    "[CircuitBreaker:%s] Probe request FAILED. Re-tripping HALF_OPEN -> OPEN.",
                    self.name
                )
                self._state = self.STATE_OPEN
            elif self._failure_count >= self.failure_threshold:
                if self._state != self.STATE_OPEN:
                    logger.error(
                        "[CircuitBreaker:%s] Failure threshold reached (%d >= %d). Tripping CLOSED -> OPEN.",
                        self.name, self._failure_count, self.failure_threshold
                    )
                self._state = self.STATE_OPEN

    def reset(self) -> None:
        """Force resets the circuit breaker to CLOSED."""
        with self._lock:
            self._state = self.STATE_CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self._half_open_trials = 0

    def call(self, fn: Callable, *args, **kwargs) -> Any:
        """
        Executes fn(*args, **kwargs) through the circuit breaker.
        Raises CircuitBreakerOpenException if the circuit is OPEN.
        """
        if not self.allow_request():
            remaining = 0.0
            if self._last_failure_time:
                remaining = max(0.0, self.recovery_timeout - (time.monotonic() - self._last_failure_time))
            raise CircuitBreakerOpenException(self.name, remaining)

        try:
            result = fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(exc)
            raise
