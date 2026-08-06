"""Error classification, diagnostics, and retry policy.

Classifies HTTP errors into concrete categories with structured diagnostics.
Determines retry/rotation/cooldown actions per error type.
"""

import logging
import random
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from crawler.config import RetryConfig

logger = logging.getLogger(__name__)


# ── Error Categories ────────────────────────────────────────────────────────

class ErrorCategory(Enum):
    SUCCESS = "success"
    RATE_LIMITED_429 = "rate_limited"
    BLOCKED_490 = "blocked"
    BLOCKED_403 = "forbidden"
    PROXY_AUTH_407 = "proxy_auth"
    NOT_FOUND = "not_found"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    CONNECTION_RESET = "connection_reset"
    DNS_FAILURE = "dns_failure"
    TCP_TIMEOUT = "tcp_timeout"
    TCP_REFUSED = "tcp_refused"
    TLS_FAILURE = "tls_failure"
    SSL_ERROR = "ssl_error"
    JSON_PARSE_FAILURE = "json_parse"
    UNEXPECTED_HTML = "unexpected_html"
    EMPTY_RESPONSE = "empty_response"
    UNKNOWN = "unknown"


class RetryAction(Enum):
    RETRY_SAME_PROXY = "retry_same"
    RETRY_ROTATE_PROXY = "retry_rotate"
    LONG_COOLDOWN = "long_cooldown"
    SHORT_COOLDOWN = "short_cooldown"
    DISCARD_SESSION = "discard_session"
    CONFIG_PROBLEM = "config_problem"
    ABORT = "abort"


@dataclass
class Diagnostics:
    """Structured diagnostic information for a failed request."""
    session_id: str = ""
    target_url: str = ""
    status_code: int = 0
    error_category: ErrorCategory = ErrorCategory.UNKNOWN
    retryable: bool = False
    recommended_action: str = ""
    exception_class: str = ""
    exception_message: str = ""
    curl_error_code: int = 0
    proxy_endpoint: str = ""
    retry_count: int = 0
    timestamp: float = 0.0
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "target_url": self.target_url,
            "status_code": self.status_code,
            "error_category": self.error_category.value,
            "retryable": self.retryable,
            "recommended_action": self.recommended_action,
            "exception_class": self.exception_class,
            "exception_message": self.exception_message,
            "curl_error_code": self.curl_error_code,
            "proxy_endpoint": self.proxy_endpoint,
            "retry_count": self.retry_count,
        }


@dataclass
class ErrorClassification:
    category: ErrorCategory
    action: RetryAction
    cooldown_seconds: int = 0
    diagnostics: Diagnostics = field(default_factory=Diagnostics)


# ── Error Classification ────────────────────────────────────────────────────

def classify_error(
    status_code: int = 0,
    exception: Exception = None,
    response_body: str = "",
    diagnostics: Diagnostics | None = None,
) -> ErrorClassification:
    """Classify an error with rich diagnostics."""

    diag = diagnostics or Diagnostics()

    # ── Exception-based errors ──────────────────────────────────────────
    if exception is not None:
        exc_name = type(exception).__name__
        exc_msg = str(exception)
        diag.exception_class = exc_name
        diag.exception_message = exc_msg[:200]

        # curl_cffi specific errors
        if hasattr(exception, "code"):
            diag.curl_error_code = getattr(exception, "code", 0)

        # DNS failures
        if ("DNS" in exc_name or "NameResolution" in exc_name
                or "getaddrinfo" in exc_msg or "Name or service not known" in exc_msg):
            diag.error_category = ErrorCategory.DNS_FAILURE
            diag.retryable = False
            diag.recommended_action = "discard_session"
            return ErrorClassification(
                ErrorCategory.DNS_FAILURE, RetryAction.DISCARD_SESSION, 30, diag)

        # TCP timeout
        if "Timeout" in exc_name and "connect" in exc_msg.lower():
            diag.error_category = ErrorCategory.TCP_TIMEOUT
            diag.retryable = True
            diag.recommended_action = "rotate_proxy"
            return ErrorClassification(
                ErrorCategory.TCP_TIMEOUT, RetryAction.RETRY_ROTATE_PROXY, 15, diag)

        # TLS handshake failure
        if ("SSL" in exc_name or "TLS" in exc_name
                or "handshake" in exc_msg.lower()
                or "certificate" in exc_msg.lower()):
            diag.error_category = ErrorCategory.TLS_FAILURE
            diag.retryable = False
            diag.recommended_action = "discard_session"
            return ErrorClassification(
                ErrorCategory.TLS_FAILURE, RetryAction.DISCARD_SESSION, 60, diag)

        # Connection refused
        if "ConnectionRefused" in exc_name or "refused" in exc_msg.lower():
            diag.error_category = ErrorCategory.TCP_REFUSED
            diag.retryable = True
            diag.recommended_action = "rotate_proxy"
            return ErrorClassification(
                ErrorCategory.TCP_REFUSED, RetryAction.RETRY_ROTATE_PROXY, 15, diag)

        # Connection reset
        if ("ConnectionReset" in exc_name or "BrokenPipe" in exc_name
                or "reset" in exc_msg.lower()):
            diag.error_category = ErrorCategory.CONNECTION_RESET
            diag.retryable = True
            diag.recommended_action = "rotate_proxy"
            return ErrorClassification(
                ErrorCategory.CONNECTION_RESET, RetryAction.RETRY_ROTATE_PROXY, 10, diag)

        # Generic timeout
        if "Timeout" in exc_name:
            diag.error_category = ErrorCategory.TIMEOUT
            diag.retryable = True
            diag.recommended_action = "cooldown"
            return ErrorClassification(
                ErrorCategory.TIMEOUT, RetryAction.SHORT_COOLDOWN, 10, diag)

        # Generic connection error
        if "Connection" in exc_name:
            diag.error_category = ErrorCategory.CONNECTION_RESET
            diag.retryable = True
            diag.recommended_action = "rotate_proxy"
            return ErrorClassification(
                ErrorCategory.CONNECTION_RESET, RetryAction.RETRY_ROTATE_PROXY, 15, diag)

        # Unknown exception
        diag.retryable = True
        diag.recommended_action = "cooldown"
        return ErrorClassification(
            ErrorCategory.UNKNOWN, RetryAction.SHORT_COOLDOWN, 30, diag)

    # ── HTTP status-based errors ────────────────────────────────────────
    diag.status_code = status_code

    if status_code == 490:
        diag.error_category = ErrorCategory.BLOCKED_490
        diag.retryable = True
        diag.recommended_action = "rotate_proxy"
        return ErrorClassification(
            ErrorCategory.BLOCKED_490, RetryAction.RETRY_ROTATE_PROXY, 120, diag)

    if status_code == 429:
        diag.error_category = ErrorCategory.RATE_LIMITED_429
        diag.retryable = True
        diag.recommended_action = "cooldown"
        return ErrorClassification(
            ErrorCategory.RATE_LIMITED_429, RetryAction.LONG_COOLDOWN, 60, diag)

    if status_code == 403:
        diag.error_category = ErrorCategory.BLOCKED_403
        diag.retryable = True
        diag.recommended_action = "rotate_proxy"
        return ErrorClassification(
            ErrorCategory.BLOCKED_403, RetryAction.RETRY_ROTATE_PROXY, 60, diag)

    if status_code == 407:
        diag.error_category = ErrorCategory.PROXY_AUTH_407
        diag.retryable = False
        diag.recommended_action = "config_problem"
        return ErrorClassification(
            ErrorCategory.PROXY_AUTH_407, RetryAction.CONFIG_PROBLEM, 0, diag)

    if status_code == 404:
        diag.error_category = ErrorCategory.NOT_FOUND
        diag.retryable = False
        diag.recommended_action = "abort"
        return ErrorClassification(
            ErrorCategory.NOT_FOUND, RetryAction.ABORT, 0, diag)

    if status_code >= 500:
        diag.error_category = ErrorCategory.SERVER_ERROR
        diag.retryable = True
        diag.recommended_action = "cooldown"
        return ErrorClassification(
            ErrorCategory.SERVER_ERROR, RetryAction.SHORT_COOLDOWN, 15, diag)

    # ── Success ─────────────────────────────────────────────────────────
    diag.error_category = ErrorCategory.SUCCESS
    return ErrorClassification(
        ErrorCategory.SUCCESS, RetryAction.ABORT, 0, diag)


def classify_response_content(
    data: dict | None,
    status_code: int,
    diagnostics: Diagnostics | None = None,
) -> ErrorCategory | None:
    """Classify based on response content (not HTTP status).

    Returns None if content is fine.
    Returns ErrorCategory if content indicates a problem.
    """
    diag = diagnostics or Diagnostics()

    if data is None:
        return None

    if not data:
        diag.error_category = ErrorCategory.EMPTY_RESPONSE
        return ErrorCategory.EMPTY_RESPONSE

    # Check for HTML instead of JSON (anti-bot page)
    if "html" in str(data.get("content_type", "")):
        diag.error_category = ErrorCategory.UNEXPECTED_HTML
        return ErrorCategory.UNEXPECTED_HTML

    # Check for JSON parse failure indicators
    if isinstance(data, str) and len(data) > 0:
        diag.error_category = ErrorCategory.JSON_PARSE_FAILURE
        return ErrorCategory.JSON_PARSE_FAILURE

    return None


# ── Retry Policy ────────────────────────────────────────────────────────────

def calculate_backoff(attempt: int, config: RetryConfig) -> float:
    """Calculate backoff delay with jitter."""
    delay = min(config.base_delay * (config.backoff_multiplier ** attempt), config.max_delay)
    jitter = delay * config.jitter
    return delay + random.uniform(-jitter, jitter)


class RetryPolicy:
    """Determines whether to retry based on error type and retry count."""

    def __init__(self, config: RetryConfig | None = None):
        self.config = config or RetryConfig()

    def should_retry(self, error_category: ErrorCategory, attempt: int) -> bool:
        """Check if a retry is allowed for this error and attempt number."""
        if attempt >= self.config.max_retries:
            return False

        # Never retry these
        if error_category in (
            ErrorCategory.SUCCESS,
            ErrorCategory.NOT_FOUND,
            ErrorCategory.PROXY_AUTH_407,
        ):
            return False

        # Always rotate and retry these
        if error_category in (
            ErrorCategory.BLOCKED_490,
            ErrorCategory.BLOCKED_403,
            ErrorCategory.TLS_FAILURE,
            ErrorCategory.DNS_FAILURE,
            ErrorCategory.CONNECTION_RESET,
            ErrorCategory.TCP_TIMEOUT,
            ErrorCategory.TCP_REFUSED,
        ):
            return True

        # Rate limiting — retry up to max
        if error_category == ErrorCategory.RATE_LIMITED_429:
            return attempt < self.config.max_429_retries

        # Server errors — limited retries
        if error_category == ErrorCategory.SERVER_ERROR:
            return attempt < self.config.max_5xx_retries

        # Timeouts — limited retries
        if error_category == ErrorCategory.TIMEOUT:
            return attempt < self.config.max_timeout_retries

        # Content errors — retry once
        if error_category in (
            ErrorCategory.JSON_PARSE_FAILURE,
            ErrorCategory.UNEXPECTED_HTML,
            ErrorCategory.EMPTY_RESPONSE,
        ):
            return attempt < 1

        return attempt < self.config.max_retries

    def get_cooldown(self, error_category: ErrorCategory) -> int:
        """Get cooldown duration for this error type."""
        cooldowns = {
            ErrorCategory.BLOCKED_490: 120,
            ErrorCategory.BLOCKED_403: 60,
            ErrorCategory.PROXY_AUTH_407: 0,
            ErrorCategory.RATE_LIMITED_429: 60,
            ErrorCategory.SERVER_ERROR: 15,
            ErrorCategory.TIMEOUT: 10,
            ErrorCategory.CONNECTION_RESET: 15,
            ErrorCategory.TCP_TIMEOUT: 15,
            ErrorCategory.TCP_REFUSED: 15,
            ErrorCategory.TLS_FAILURE: 60,
            ErrorCategory.SSL_ERROR: 60,
            ErrorCategory.DNS_FAILURE: 30,
            ErrorCategory.JSON_PARSE_FAILURE: 10,
            ErrorCategory.UNEXPECTED_HTML: 10,
            ErrorCategory.EMPTY_RESPONSE: 5,
            ErrorCategory.UNKNOWN: 30,
        }
        return cooldowns.get(error_category, 30)

    def needs_rotation(self, error_category: ErrorCategory) -> bool:
        """Check if error requires proxy rotation."""
        return error_category in (
            ErrorCategory.BLOCKED_490,
            ErrorCategory.BLOCKED_403,
            ErrorCategory.TLS_FAILURE,
            ErrorCategory.DNS_FAILURE,
            ErrorCategory.CONNECTION_RESET,
            ErrorCategory.TCP_TIMEOUT,
            ErrorCategory.TCP_REFUSED,
        )

    def discard_session(self, error_category: ErrorCategory) -> bool:
        """Check if error means current session should be discarded."""
        return error_category in (
            ErrorCategory.DNS_FAILURE,
            ErrorCategory.TLS_FAILURE,
            ErrorCategory.PROXY_AUTH_407,
        )
