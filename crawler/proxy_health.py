"""PostgreSQL-backed proxy session health tracking.

Replaces the former SQLite implementation; writes directly to the `proxy_sessions`
table defined in db.models (same DB the API reads). No business logic.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from db import sync

logger = logging.getLogger(__name__)


def _dt(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
    """PostgreSQL repository for proxy session health data."""

    def __init__(self, db_path=None):
        # db_path kept for backward-compat signature; ignored (Postgres now).
        sync.ensure_schema()
        self.conn = sync.connect()

    def _now(self) -> datetime:
        return _now()

    # ── Write ────────────────────────────────────────────────────────────
    def upsert(self, record: ProxySessionRecord) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO proxy_sessions (
                session_id, created_at, last_used, request_count, success_count,
                error_490_count, error_429_count, error_5xx_count, timeout_count,
                total_latency_ms, is_quarantined, quarantine_reason, quarantine_until
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (session_id) DO UPDATE SET
                last_used = EXCLUDED.last_used,
                request_count = EXCLUDED.request_count,
                success_count = EXCLUDED.success_count,
                error_490_count = EXCLUDED.error_490_count,
                error_429_count = EXCLUDED.error_429_count,
                error_5xx_count = EXCLUDED.error_5xx_count,
                timeout_count = EXCLUDED.timeout_count,
                total_latency_ms = EXCLUDED.total_latency_ms,
                is_quarantined = EXCLUDED.is_quarantined,
                quarantine_reason = EXCLUDED.quarantine_reason,
                quarantine_until = EXCLUDED.quarantine_until
            """,
            (
                record.session_id,
                _dt(record.created_at) or _now(),
                _dt(record.last_used),
                record.request_count, record.success_count,
                record.error_490_count, record.error_429_count,
                record.error_5xx_count, record.timeout_count,
                record.total_latency_ms, bool(record.is_quarantined),
                record.quarantine_reason, _dt(record.quarantine_until),
            ),
        )
        self.conn.commit()
        cur.close()

    def record_success(self, session_id: str, latency_ms: int) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE proxy_sessions SET
                request_count = request_count + 1,
                success_count = success_count + 1,
                total_latency_ms = total_latency_ms + %s,
                last_used = %s
            WHERE session_id = %s
            """,
            (latency_ms, _now(), session_id),
        )
        self.conn.commit()
        cur.close()

    def record_error(self, session_id: str, error_type: str) -> None:
        col_map = {
            "490": "error_490_count",
            "429": "error_429_count",
            "5xx": "error_5xx_count",
            "timeout": "timeout_count",
        }
        col = col_map.get(error_type, "error_5xx_count")
        # column is from a fixed whitelist, safe to interpolate
        cur = self.conn.cursor()
        cur.execute(
            f"""
            UPDATE proxy_sessions SET
                request_count = request_count + 1,
                {col} = {col} + 1,
                last_used = %s
            WHERE session_id = %s
            """,
            (_now(), session_id),
        )
        self.conn.commit()
        cur.close()

    def quarantine(self, session_id: str, reason: str, until: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE proxy_sessions SET
                is_quarantined = %s,
                quarantine_reason = %s,
                quarantine_until = %s
            WHERE session_id = %s
            """,
            (True, reason, _dt(until), session_id),
        )
        self.conn.commit()
        cur.close()

    def release(self, session_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE proxy_sessions SET
                is_quarantined = %s,
                quarantine_reason = %s,
                quarantine_until = %s
            WHERE session_id = %s
            """,
            (False, "", None, session_id),
        )
        self.conn.commit()
        cur.close()

    # ── Read ─────────────────────────────────────────────────────────────
    def get(self, session_id: str) -> ProxySessionRecord | None:
        cur = sync.dict_cursor(self.conn)
        cur.execute("SELECT * FROM proxy_sessions WHERE session_id = %s", (session_id,))
        row = cur.fetchone()
        cur.close()
        return self._row_to_record(row) if row else None

    def get_active_sessions(self) -> list[ProxySessionRecord]:
        now = _now()
        cur = sync.dict_cursor(self.conn)
        cur.execute(
            "SELECT * FROM proxy_sessions WHERE is_quarantined = %s OR quarantine_until < %s ORDER BY last_used",
            (False, now),
        )
        rows = cur.fetchall()
        cur.close()
        return [self._row_to_record(r) for r in rows]

    def get_quarantined_sessions(self) -> list[ProxySessionRecord]:
        now = _now()
        cur = sync.dict_cursor(self.conn)
        cur.execute(
            "SELECT * FROM proxy_sessions WHERE is_quarantined = %s AND quarantine_until >= %s",
            (True, now),
        )
        rows = cur.fetchall()
        cur.close()
        return [self._row_to_record(r) for r in rows]

    def release_expired(self) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE proxy_sessions SET is_quarantined = %s WHERE is_quarantined = %s AND quarantine_until < %s",
            (False, True, _now()),
        )
        n = cur.rowcount
        self.conn.commit()
        cur.close()
        return n

    def health_summary(self) -> dict:
        cur = sync.dict_cursor(self.conn)
        cur.execute("SELECT * FROM proxy_sessions")
        rows = cur.fetchall()
        cur.close()
        if not rows:
            return {"total": 0}
        records = [self._row_to_record(r) for r in rows]
        quarantined = sum(1 for r in records if r.is_quarantined)
        avg_latency = (
            sum(r.total_latency_ms / max(r.request_count, 1) for r in records) / len(records)
        )
        return {
            "total": len(records),
            "quarantined": quarantined,
            "active": len(records) - quarantined,
            "avg_latency_ms": int(avg_latency),
            "total_490": sum(r.error_490_count for r in records),
            "total_requests": sum(r.request_count for r in records),
        }

    def _row_to_record(self, row) -> ProxySessionRecord:
        return ProxySessionRecord(
            session_id=row["session_id"],
            created_at=str(row["created_at"]),
            last_used=str(row["last_used"]) if row["last_used"] else "",
            request_count=row["request_count"],
            success_count=row["success_count"],
            error_490_count=row["error_490_count"],
            error_429_count=row["error_429_count"],
            error_5xx_count=row["error_5xx_count"],
            timeout_count=row["timeout_count"],
            total_latency_ms=row["total_latency_ms"],
            is_quarantined=1 if row["is_quarantined"] else 0,
            quarantine_reason=row["quarantine_reason"] or "",
            quarantine_until=str(row["quarantine_until"]) if row["quarantine_until"] else "",
        )

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass