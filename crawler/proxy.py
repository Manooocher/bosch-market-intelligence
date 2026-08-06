"""Proxy-Cheap gateway manager.

Handles credential loading, session generation, rotation, health tracking,
and structured diagnostics for every failure.
No Torob-specific logic. No HTTP logic.
"""

import logging
import random
import string
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from crawler.config import ProxyConfig
from crawler.proxy_health import ProxyHealthStore, ProxySessionRecord

logger = logging.getLogger(__name__)


@dataclass
class ProxySession:
    """Active proxy session with URL, metadata, and diagnostics."""
    session_id: str
    proxy_url: str
    created_at: datetime
    last_used: datetime
    request_count: int = 0
    diagnostics: dict = field(default_factory=dict)


@dataclass
class RequestDiagnostic:
    """Structured diagnostic for one failed request."""
    session_id: str = ""
    proxy_endpoint: str = ""
    target_url: str = ""
    error_category: str = ""
    exception_class: str = ""
    exception_message: str = ""
    http_status: int = 0
    retry_count: int = 0
    timestamp: float = 0.0
    recommended_action: str = ""
    curl_error_code: int = 0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "proxy_endpoint": self.proxy_endpoint,
            "target_url": self.target_url,
            "error_category": self.error_category,
            "http_status": self.http_status,
            "exception_class": self.exception_class,
            "exception_message": self.exception_message[:200],
            "retry_count": self.retry_count,
            "recommended_action": self.recommended_action,
            "curl_error_code": self.curl_error_code,
        }


class ProxyManager:
    """Manages Proxy-Cheap residential proxy gateway.

    Responsibilities:
    - Load credentials from environment
    - Generate proxy URLs with session IDs
    - Rotate sessions based on triggers
    - Track session health
    - Quarantine bad sessions
    - Record structured diagnostics on failure
    """

    def __init__(self, config: ProxyConfig, health_store: ProxyHealthStore):
        self.config = config
        self.health_store = health_store
        self._current_session: ProxySession | None = None
        self._rotate_after = config.rotate_every_recovery
        self._request_counter = 0
        self._diagnostics: list[RequestDiagnostic] = []

    def _generate_session_id(self) -> str:
        rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        ts = int(time.time())
        return f"sess_{rand}_{ts}"

    def _build_proxy_url(self, session_id: str) -> str:
        c = self.config
        # Proxy-Cheap residential: each connection gets a new rotating IP.
        # Session management not supported through URL format.
        # Rotation happens by creating new connections.
        return f"http://{c.username}:{c.password}@{c.gateway_host}:{c.gateway_port}"

    def get_current(self) -> ProxySession | None:
        """Return current session, creating one if needed."""
        if self._current_session is None:
            return self.create_session()
        self._request_counter += 1
        self._current_session.request_count += 1
        self._current_session.last_used = datetime.now(timezone.utc)
        return self._current_session

    def create_session(self, reason: str = "initial") -> ProxySession:
        """Create a new proxy session."""
        if not self.config.enabled:
            return ProxySession(
                session_id="direct",
                proxy_url="",
                created_at=datetime.now(timezone.utc),
                last_used=datetime.now(timezone.utc),
            )

        session_id = self._generate_session_id()
        proxy_url = self._build_proxy_url(session_id)
        now = datetime.now(timezone.utc)

        session = ProxySession(
            session_id=session_id,
            proxy_url=proxy_url,
            created_at=now,
            last_used=now,
        )
        self._current_session = session
        self._request_counter = 0

        # Record in health store
        record = ProxySessionRecord(
            session_id=session_id,
            created_at=now.isoformat(),
            last_used=now.isoformat(),
        )
        self.health_store.upsert(record)

        logger.info(f"Created proxy session {session_id} (reason: {reason})")
        return session

    def rotate(self, reason: str = "scheduled") -> ProxySession:
        """Rotate to a new proxy session."""
        return self.create_session(reason=reason)

    def should_rotate(self) -> bool:
        """Check if rotation is needed based on request count."""
        return self._request_counter >= self._rotate_after

    def record_success(self, session_id: str, latency_ms: int) -> None:
        """Record a successful request for the session."""
        self.health_store.record_success(session_id, latency_ms)

    def record_error(self, session_id: str, error_type: str) -> None:
        """Record a failed request for the session."""
        self.health_store.record_error(session_id, error_type)

    def record_diagnostics(self, diag: RequestDiagnostic) -> None:
        """Record structured diagnostic for a failed request."""
        self._diagnostics.append(diag)
        # Log with full context
        logger.warning(
            "Request failed: "
            f"session={diag.session_id} "
            f"status={diag.http_status} "
            f"category={diag.error_category} "
            f"exception={diag.exception_class} "
            f"action={diag.recommended_action} "
            f"url={diag.target_url[:80]}"
        )

    def quarantine_current(self, reason: str, duration_minutes: int = None) -> None:
        """Quarantine the current session."""
        if self._current_session is None:
            return

        duration = duration_minutes or self.config.quarantine_duration_seconds // 60
        until = (datetime.now(timezone.utc) + timedelta(minutes=duration)).isoformat()

        self.health_store.quarantine(
            self._current_session.session_id, reason, until
        )
        logger.warning(f"Quarantined session {self._current_session.session_id} "
                       f"until {until} (reason: {reason})")
        self._current_session = None

    def get_health_summary(self) -> dict:
        """Get health summary of all sessions."""
        return self.health_store.health_summary()

    def get_diagnostics(self, limit: int = 50) -> list[dict]:
        """Get recent diagnostics."""
        return [d.to_dict() for d in self._diagnostics[-limit:]]

    def get_diagnostic_summary(self) -> dict:
        """Summarize diagnostic patterns."""
        if not self._diagnostics:
            return {"total": 0}

        from collections import Counter
        cat_counts = Counter(d.error_category for d in self._diagnostics)
        action_counts = Counter(d.recommended_action for d in self._diagnostics)

        return {
            "total": len(self._diagnostics),
            "by_category": dict(cat_counts),
            "by_action": dict(action_counts),
            "recent": self._diagnostics[-5:] if self._diagnostics else [],
        }

    def set_rotate_after(self, count: int):
        """Change rotation trigger (for different modes)."""
        self._rotate_after = count
