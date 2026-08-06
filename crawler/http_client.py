"""Single HTTP client for all crawler operations.

Uses curl_cffi for TLS fingerprint impersonation.
Integrates with proxy manager, circuit breaker, metrics, retry policy.
NO other HTTP implementation should exist in the project.
"""

import json
import logging
import time
import traceback
from dataclasses import dataclass

from curl_cffi.requests import Session

from crawler.config import CrawlerConfig
from crawler.fingerprint import FingerprintManager
from crawler.proxy import ProxyManager, RequestDiagnostic
from crawler.circuit_breaker import CircuitBreaker
from crawler.retry import RetryPolicy, classify_error, ErrorCategory
from crawler.metrics import MetricsCollector

logger = logging.getLogger(__name__)


@dataclass
class Response:
    """Unified HTTP response."""
    status_code: int = 0
    data: dict = None
    success: bool = False
    proxy_session: str = ""
    retries: int = 0
    duration_ms: int = 0
    error: str = ""


class HttpClient:
    """Production HTTP client with retry, proxy, circuit breaker, and metrics.

    Single implementation for all HTTP operations.
    """

    def __init__(
        self,
        config: CrawlerConfig,
        proxy_manager: ProxyManager,
        fingerprint: FingerprintManager,
        circuit_breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
        metrics: MetricsCollector,
        mode: str = "default",
    ):
        self.config = config
        self.proxy_manager = proxy_manager
        self.fingerprint = fingerprint
        self.circuit_breaker = circuit_breaker
        self.retry_policy = retry_policy
        self.metrics = metrics
        self.mode = mode

        self._session: Session | None = None
        self._session_proxy_url: str = ""
        self._setup_session()

    def _setup_session(self) -> None:
        """Create or refresh the curl_cffi session with current proxy."""
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass

        self._session = Session(impersonate="chrome")
        headers = self.fingerprint.get_headers()
        self._session.headers.update(headers)

        session = self.proxy_manager.get_current()
        if session and session.proxy_url:
            self._session.proxies = {
                "http": session.proxy_url,
                "https": session.proxy_url,
            }
            self._session_proxy_url = session.session_id
            logger.debug(f"Session using proxy {session.session_id}")

    def request(self, url: str, params: dict = None) -> Response:
        """Execute an HTTP request with full lifecycle handling.

        Circuit breaker → rate limit → execute → classify → retry → metrics.
        """
        if not self.circuit_breaker.allow_request():
            logger.warning("Circuit breaker OPEN, request rejected")
            return Response(error="circuit_breaker_open")

        session = self.proxy_manager.get_current()
        if session and self.proxy_manager.should_rotate():
            self.proxy_manager.rotate(reason="scheduled")
            self.fingerprint.rotate_identity()
            self._setup_session()
            self.metrics.record_proxy_rotation("scheduled")

        start_time = time.time()

        for attempt in range(self.config.retry.max_retries):
            try:
                r = self._session.request(
                    "GET", url, params=params, timeout=self.config.timeouts.total
                )
                status = r.status_code
                duration_ms = int((time.time() - start_time) * 1000)

                # Classify error from status code
                classification = classify_error(status_code=status)

                if classification.category == ErrorCategory.SUCCESS:
                    try:
                        data = r.json()
                    except (json.JSONDecodeError, ValueError):
                        data = {}

                    self.circuit_breaker.record_success()
                    self.metrics.record_request(
                        self.mode, status, duration_ms,
                        self._session_proxy_url, attempt
                    )
                    if session:
                        self.proxy_manager.record_success(session.session_id, duration_ms)

                    return Response(
                        status_code=status, data=data, success=True,
                        proxy_session=self._session_proxy_url,
                        retries=attempt, duration_ms=duration_ms,
                    )

                # Non-success: record diagnostic
                diag = RequestDiagnostic(
                    session_id=self._session_proxy_url,
                    target_url=url,
                    http_status=status,
                    error_category=classification.category.value,
                    recommended_action=classification.action.value,
                    retry_count=attempt,
                    timestamp=time.time(),
                )
                self.proxy_manager.record_diagnostics(diag)

                self.metrics.record_request(
                    self.mode, status, duration_ms,
                    self._session_proxy_url, attempt
                )
                self.circuit_breaker.record_failure()
                if session:
                    self.proxy_manager.record_error(session.session_id, classification.category.value)

                if not self.retry_policy.should_retry(classification.category, attempt):
                    return Response(
                        status_code=status, success=False,
                        proxy_session=self._session_proxy_url,
                        retries=attempt, duration_ms=duration_ms,
                        error=f"http_{status}_{classification.category.value}",
                    )

                # Discard session if needed
                if self.retry_policy.discard_session(classification.category):
                    self.proxy_manager.quarantine_current(
                        classification.category.value)
                    self.fingerprint.rotate_identity()
                    self._setup_session()
                    self.metrics.record_proxy_rotation(f"discard_{classification.category.value}")

                # Rotate proxy if needed
                elif self.retry_policy.needs_rotation(classification.category):
                    self.proxy_manager.rotate(reason=classification.category.value)
                    self.fingerprint.rotate_identity()
                    self._setup_session()
                    self.metrics.record_proxy_rotation(classification.category.value)

                # Apply cooldown
                if classification.cooldown_seconds > 0:
                    time.sleep(classification.cooldown_seconds)

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                classification = classify_error(exception=e)

                diag = RequestDiagnostic(
                    session_id=self._session_proxy_url,
                    target_url=url,
                    error_category=classification.category.value,
                    exception_class=type(e).__name__,
                    exception_message=str(e)[:200],
                    recommended_action=classification.action.value,
                    retry_count=attempt,
                    timestamp=time.time(),
                )
                self.proxy_manager.record_diagnostics(diag)

                self.metrics.record_request(
                    self.mode, 0, duration_ms,
                    self._session_proxy_url, attempt
                )
                self.circuit_breaker.record_failure()
                if session:
                    self.proxy_manager.record_error(session.session_id, classification.category.value)

                if not self.retry_policy.should_retry(classification.category, attempt):
                    return Response(
                        success=False, proxy_session=self._session_proxy_url,
                        retries=attempt, duration_ms=duration_ms,
                        error=f"{classification.category.value}: {str(e)[:100]}",
                    )

                # Discard session if needed
                if self.retry_policy.discard_session(classification.category):
                    self.proxy_manager.quarantine_current(classification.category.value)
                    self.fingerprint.rotate_identity()
                    self._setup_session()
                    self.metrics.record_proxy_rotation(f"discard_{classification.category.value}")

                # Rotate proxy if needed
                elif self.retry_policy.needs_rotation(classification.category):
                    self.proxy_manager.rotate(reason=classification.category.value)
                    self.fingerprint.rotate_identity()
                    self._setup_session()
                    self.metrics.record_proxy_rotation(classification.category.value)

                # Apply cooldown
                if classification.cooldown_seconds > 0:
                    time.sleep(classification.cooldown_seconds)

        total_ms = int((time.time() - start_time) * 1000)
        return Response(
            success=False, proxy_session=self._session_proxy_url,
            retries=self.config.retry.max_retries, duration_ms=total_ms,
            error="max_retries_exceeded",
        )

    def close(self) -> None:
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
