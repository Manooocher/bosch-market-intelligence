"""SQLite storage for Watch List, candidates, review queue, and logs.

Tables:
- watch_list: Main product mapping (Nabkade → Torob)
- match_candidates: All scored candidates per Nabkade product
- review_queue: Products requiring manual review
- matching_logs: Audit trail of matching decisions
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone

from matcher.confidence import ConfidenceLevel, ConfidenceResult
from matcher.scorer import ScoredMatch
from matcher.index import NabkadeProduct

logger = logging.getLogger(__name__)


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS watch_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nabkade_product_id TEXT NOT NULL,
    nabkade_url TEXT,
    nabkade_title TEXT,
    nabkade_category TEXT,
    nabkade_brand TEXT,
    nabkade_price TEXT,
    canonical_sku TEXT,
    normalized_category TEXT,
    preferred_torob_id TEXT,
    preferred_torob_url TEXT,
    preferred_torob_title TEXT,
    all_torob_ids TEXT,
    match_count INTEGER DEFAULT 0,
    confidence_score REAL DEFAULT 0.0,
    confidence_level TEXT DEFAULT 'none',
    match_method TEXT DEFAULT 'none',
    status TEXT DEFAULT 'no_match',
    review_state TEXT DEFAULT 'auto_accepted',
    reviewer TEXT,
    review_notes TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS match_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nabkade_product_id TEXT NOT NULL,
    torob_product_id TEXT NOT NULL,
    score REAL DEFAULT 0.0,
    signals TEXT,
    match_source TEXT,
    rank INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nabkade_product_id TEXT NOT NULL,
    nabkade_title TEXT,
    nabkade_url TEXT,
    nabkade_price TEXT,
    candidate_list TEXT,
    confidence_score REAL DEFAULT 0.0,
    confidence_level TEXT DEFAULT 'low',
    review_reason TEXT,
    status TEXT DEFAULT 'pending',
    reviewer TEXT,
    notes TEXT,
    created_at TEXT,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS matching_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nabkade_product_id TEXT,
    action TEXT,
    details TEXT,
    timestamp TEXT
);

CREATE INDEX IF NOT EXISTS idx_watch_list_nabkade ON watch_list(nabkade_product_id);
CREATE INDEX IF NOT EXISTS idx_watch_list_torob ON watch_list(preferred_torob_id);
CREATE INDEX IF NOT EXISTS idx_watch_list_confidence ON watch_list(confidence_level);
CREATE INDEX IF NOT EXISTS idx_watch_list_status ON watch_list(status);
CREATE INDEX IF NOT EXISTS idx_candidates_nabkade ON match_candidates(nabkade_product_id);
CREATE INDEX IF NOT EXISTS idx_candidates_torob ON match_candidates(torob_product_id);
CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(status);
CREATE INDEX IF NOT EXISTS idx_review_queue_nabkade ON review_queue(nabkade_product_id);
CREATE INDEX IF NOT EXISTS idx_logs_nabkade ON matching_logs(nabkade_product_id);
"""


class WatchListStore:
    """SQLite-backed storage for the Product Matcher."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.executescript(_SCHEMA_SQL)
        self.conn.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Watch List ──────────────────────────────────────────────────────

    def upsert_watch_list(
        self,
        nabkade: NabkadeProduct,
        confidence: ConfidenceResult,
        best_match: ScoredMatch | None,
        torob_url: str = "",
        torob_title: str = "",
    ) -> None:
        """Insert or update a watch list entry."""
        now = self._now()
        status = "matched" if confidence.preferred_torob_id else "no_match"
        review_state = "auto_accepted"
        if confidence.needs_review:
            review_state = "pending_review"
        if confidence.level == ConfidenceLevel.NONE:
            review_state = "pending_review" if confidence.match_count > 0 else "auto_rejected"

        method = best_match.match_source if best_match else "none"

        self.conn.execute("""
            INSERT OR REPLACE INTO watch_list (
                nabkade_product_id, nabkade_url, nabkade_title,
                nabkade_category, nabkade_brand, nabkade_price,
                canonical_sku, normalized_category,
                preferred_torob_id, preferred_torob_url, preferred_torob_title,
                all_torob_ids, match_count, confidence_score, confidence_level,
                match_method, status, review_state,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nabkade.product_id,
            nabkade.product_url,
            nabkade.title,
            nabkade.category,
            nabkade.brand,
            nabkade.price,
            ",".join(nabkade.canonical_skus),
            nabkade.normalized_category,
            confidence.preferred_torob_id,
            torob_url,
            torob_title,
            json.dumps(confidence.all_torob_ids),
            confidence.match_count,
            confidence.score,
            confidence.level.value,
            method,
            status,
            review_state,
            now,
            now,
        ))
        self.conn.commit()

    # ── Match Candidates ────────────────────────────────────────────────

    def insert_candidates(
        self,
        nabkade_id: str,
        scored: list[ScoredMatch],
    ) -> None:
        """Store all scored candidates for a Nabkade product."""
        now = self._now()
        for rank, s in enumerate(scored, 1):
            self.conn.execute("""
                INSERT INTO match_candidates (
                    nabkade_product_id, torob_product_id, score,
                    signals, match_source, rank, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                nabkade_id,
                s.torob_product_id,
                s.score,
                json.dumps(s.signals),
                s.match_source,
                rank,
                now,
            ))
        self.conn.commit()

    # ── Review Queue ────────────────────────────────────────────────────

    def insert_review(
        self,
        nabkade: NabkadeProduct,
        confidence: ConfidenceResult,
        candidates_text: str,
    ) -> None:
        """Add a product to the manual review queue."""
        now = self._now()
        self.conn.execute("""
            INSERT INTO review_queue (
                nabkade_product_id, nabkade_title, nabkade_url,
                nabkade_price, candidate_list, confidence_score,
                confidence_level, review_reason, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (
            nabkade.product_id,
            nabkade.title,
            nabkade.product_url,
            nabkade.price,
            candidates_text,
            confidence.score,
            confidence.level.value,
            confidence.reason,
            now,
        ))
        self.conn.commit()

    # ── Logs ────────────────────────────────────────────────────────────

    def log(self, nabkade_id: str, action: str, details: str = "") -> None:
        """Write a matching log entry."""
        self.conn.execute("""
            INSERT INTO matching_logs (nabkade_product_id, action, details, timestamp)
            VALUES (?, ?, ?, ?)
        """, (nabkade_id, action, details, self._now()))
        self.conn.commit()

    # ── Queries ─────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get summary statistics."""
        cur = self.conn.cursor()
        stats: dict = {}

        cur.execute("SELECT COUNT(*) FROM watch_list")
        stats["total"] = cur.fetchone()[0]

        cur.execute("SELECT confidence_level, COUNT(*) FROM watch_list GROUP BY confidence_level")
        for row in cur.fetchall():
            stats[f"confidence_{row[0]}"] = row[1]

        cur.execute("SELECT status, COUNT(*) FROM watch_list GROUP BY status")
        for row in cur.fetchall():
            stats[f"status_{row[0]}"] = row[1]

        cur.execute("SELECT COUNT(*) FROM review_queue WHERE status='pending'")
        stats["review_pending"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM match_candidates")
        stats["total_candidates"] = cur.fetchone()[0]

        return stats

    def get_watch_list(self) -> list[dict]:
        """Get all watch list entries."""
        cur = self.conn.execute("SELECT * FROM watch_list ORDER BY confidence_level, nabkade_product_id")
        return [dict(row) for row in cur.fetchall()]

    def get_review_queue(self) -> list[dict]:
        """Get pending review items."""
        cur = self.conn.execute(
            "SELECT * FROM review_queue WHERE status='pending' ORDER BY confidence_score ASC"
        )
        return [dict(row) for row in cur.fetchall()]

    def close(self) -> None:
        self.conn.close()
