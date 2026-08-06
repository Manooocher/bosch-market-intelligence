"""Persistent proxy health tracking.

SQLite-backed repository for proxy session health data.
Survives process restarts.
No business logic — only data access.
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from crawler.config import PROXY_HEALTH_DB

logger = logging.getLogger(__name__)


@dataclass
class ProxySessionRecord:
    """One row in proxy_sessions table."""
    session_id: str = ""
    created_at: str = ""
    last_used: str = ""
    request_count: int = 0
    success_count: int = 0
    error_490_count: int = 0
    error_429_count: int = 0
    error_5xx_count: int = 0
    timeout_count: int = 0
    total_latency_ms: int = 0
    is_quarantined: int = 0
    quarantine_reason: str = ""
    quarantine_until: str = ""


class ProxyHealthStore:
    """SQLite repository for proxy session health data."""

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS proxy_sessions (
        session_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        last_used TEXT,
        request_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0,
        error_490_count INTEGER DEFAULT 0,
        error_429_count INTEGER DEFAULT 0,
        error_5xx_count INTEGER DEFAULT 0,
        timeout_count INTEGER DEFAULT 0,
        total_latency_ms INTEGER DEFAULT 0,
        is_quarantined INTEGER DEFAULT 0,
        quarantine_reason TEXT DEFAULT '',
        quarantine_until TEXT DEFAULT ''
    );
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or PROXY_HEALTH_DB
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self.conn.executescript(self._SCHEMA)
        self.conn.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Write ────────────────────────────────────────────────────────────

    def upsert(self, record: ProxySessionRecord) -> None:
        self.conn.execute("""
            INSERT OR REPLACE INTO proxy_sessions
            (session_id, created_at, last_used, request_count, success_count,
             error_490_count, error_429_count, error_5xx_count, timeout_count,
             total_latency_ms, is_quarantined, quarantine_reason, quarantine_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.session_id, record.created_at, record.last_used,
            record.request_count, record.success_count,
            record.error_490_count, record.error_429_count,
            record.error_5xx_count, record.timeout_count,
            record.total_latency_ms, record.is_quarantined,
            record.quarantine_reason, record.quarantine_until,
        ))
        self.conn.commit()

    def record_success(self, session_id: str, latency_ms: int) -> None:
        now = self._now()
        self.conn.execute("""
            UPDATE proxy_sessions SET
                request_count = request_count + 1,
                success_count = success_count + 1,
                total_latency_ms = total_latency_ms + ?,
                last_used = ?
            WHERE session_id = ?
        """, (latency_ms, now, session_id))
        self.conn.commit()

    def record_error(self, session_id: str, error_type: str) -> None:
        """error_type: '490', '429', '5xx', 'timeout'"""
        col_map = {
            "490": "error_490_count",
            "429": "error_429_count",
            "5xx": "error_5xx_count",
            "timeout": "timeout_count",
        }
        col = col_map.get(error_type, "error_5xx_count")
        now = self._now()
        self.conn.execute(f"""
            UPDATE proxy_sessions SET
                request_count = request_count + 1,
                {col} = {col} + 1,
                last_used = ?
            WHERE session_id = ?
        """, (now, session_id))
        self.conn.commit()

    def quarantine(self, session_id: str, reason: str, until: str) -> None:
        self.conn.execute("""
            UPDATE proxy_sessions SET
                is_quarantined = 1,
                quarantine_reason = ?,
                quarantine_until = ?
            WHERE session_id = ?
        """, (reason, until, session_id))
        self.conn.commit()

    def release(self, session_id: str) -> None:
        self.conn.execute("""
            UPDATE proxy_sessions SET
                is_quarantined = 0,
                quarantine_reason = '',
                quarantine_until = ''
            WHERE session_id = ?
        """, (session_id,))
        self.conn.commit()

    # ── Read ─────────────────────────────────────────────────────────────

    def get(self, session_id: str) -> ProxySessionRecord | None:
        row = self.conn.execute(
            "SELECT * FROM proxy_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return self._row_to_record(row) if row else None

    def get_active_sessions(self) -> list[ProxySessionRecord]:
        now = self._now()
        rows = self.conn.execute(
            "SELECT * FROM proxy_sessions WHERE is_quarantined = 0 OR quarantine_until < ? ORDER BY last_used",
            (now,),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get_quarantined_sessions(self) -> list[ProxySessionRecord]:
        now = self._now()
        rows = self.conn.execute(
            "SELECT * FROM proxy_sessions WHERE is_quarantined = 1 AND quarantine_until >= ?",
            (now,),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def release_expired(self) -> int:
        now = self._now()
        cur = self.conn.execute(
            "UPDATE proxy_sessions SET is_quarantined = 0 WHERE is_quarantined = 1 AND quarantine_until < ?",
            (now,),
        )
        self.conn.commit()
        return cur.rowcount

    def health_summary(self) -> dict:
        rows = self.conn.execute("SELECT * FROM proxy_sessions").fetchall()
        if not rows:
            return {"total": 0}
        records = [self._row_to_record(r) for r in rows]
        quarantined = sum(1 for r in records if r.is_quarantined)
        avg_latency = (
            sum(r.total_latency_ms / max(r.request_count, 1) for r in records) / len(records)
        )
        total_490 = sum(r.error_490_count for r in records)
        total_requests = sum(r.request_count for r in records)
        return {
            "total": len(records),
            "quarantined": quarantined,
            "active": len(records) - quarantined,
            "avg_latency_ms": int(avg_latency),
            "total_490": total_490,
            "total_requests": total_requests,
        }

    def _row_to_record(self, row) -> ProxySessionRecord:
        return ProxySessionRecord(
            session_id=row["session_id"],
            created_at=row["created_at"],
            last_used=row["last_used"],
            request_count=row["request_count"],
            success_count=row["success_count"],
            error_490_count=row["error_490_count"],
            error_429_count=row["error_429_count"],
            error_5xx_count=row["error_5xx_count"],
            timeout_count=row["timeout_count"],
            total_latency_ms=row["total_latency_ms"],
            is_quarantined=row["is_quarantined"],
            quarantine_reason=row["quarantine_reason"],
            quarantine_until=row["quarantine_until"],
        )

    def close(self):
        self.conn.close()
