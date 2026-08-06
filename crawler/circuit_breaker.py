"""Circuit breaker for HTTP operations.

State machine: CLOSED → OPEN → HALF_OPEN → CLOSED
Reusable by every crawler mode.
"""

import logging
import time
from enum import Enum

from crawler.config import CircuitBreakerConfig

logger = logging.getLogger(__name__)


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Prevents repeated failures by stopping requests when failures exceed threshold.

    - CLOSED: Normal operation. Requests pass through. Failures are counted.
    - OPEN: Fail fast. All requests rejected immediately.
    - HALF_OPEN: Test mode. One request allowed. If it succeeds → CLOSED. If it fails → OPEN.
    """

    def __init__(self, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self._state = State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0
        self._opened_at = 0

    @property
    def state(self) -> State:
        if self._state == State.OPEN:
            elapsed = time.time() - self._opened_at
            if elapsed >= self.config.cooldown_seconds:
                self._state = State.HALF_OPEN
                self._success_count = 0
                logger.info("Circuit breaker: OPEN → HALF_OPEN")
        return self._state

    def allow_request(self) -> bool:
        """Check if a request is allowed."""
        state = self.state
        if state == State.CLOSED:
            return True
        if state == State.HALF_OPEN:
            return True
        return False  # OPEN

    def record_success(self) -> None:
        """Record a successful request."""
        if self._state == State.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold_half_open:
                self._state = State.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info("Circuit breaker: HALF_OPEN → CLOSED")
        elif self._state == State.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == State.HALF_OPEN:
            self._state = State.OPEN
            self._opened_at = time.time()
            logger.warning("Circuit breaker: HALF_OPEN → OPEN")
        elif self._failure_count >= self.config.failure_threshold:
            self._state = State.OPEN
            self._opened_at = time.time()
            logger.warning(f"Circuit breaker: CLOSED → OPEN (failures: {self._failure_count})")

    def reset(self) -> None:
        """Manually reset to CLOSED."""
        self._state = State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info("Circuit breaker: manually reset to CLOSED")

    def summary(self) -> dict:
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "cooldown_remaining": max(0, self.config.cooldown_seconds - (time.time() - self._opened_at)) if self._state == State.OPEN else 0,
        }
