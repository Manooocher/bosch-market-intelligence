"""PostgreSQL storage for Watch List, candidates, review queue, and logs.

Replaces the former SQLite implementation. Writes directly to the Postgres tables
defined in db.models (watch_list, match_candidates, review_queue, matching_logs)
so the FastAPI reads the same data with no bridge.
"""

import json
import logging
from datetime import datetime, timezone

from db import sync

logger = logging.getLogger(__name__)


def _dt(v):
    if v is None or isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WatchListStore:
    """PostgreSQL-backed storage for the Product Matcher."""

    def __init__(self, db_path: str) -> None:
        sync.ensure_schema()
        self.conn = sync.connect()

    def _now(self) -> datetime:
        return _now()

    def upsert_watch_list(self, nabkade, confidence, best_match, torob_url="", torob_title=""):
        now = _now()
        status = "matched" if confidence.preferred_torob_id else "no_match"
        review_state = "auto_accepted"
        if confidence.needs_review:
            review_state = "pending_review"
        from matcher.confidence import ConfidenceLevel
        if confidence.level == ConfidenceLevel.NONE:
            review_state = "pending_review" if confidence.match_count > 0 else "auto_rejected"

        method = best_match.match_source if best_match else "none"

        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO watch_list (
                nabkade_product_id, nabkade_url, nabkade_title,
                nabkade_category, nabkade_brand, nabkade_price,
                canonical_sku, normalized_category,
                preferred_torob_id, preferred_torob_url, preferred_torob_title,
                all_torob_ids, match_count, confidence_score, confidence_level,
                match_method, status, review_state,
                created_at, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (nabkade_product_id) DO UPDATE SET
                nabkade_url = EXCLUDED.nabkade_url,
                nabkade_title = EXCLUDED.nabkade_title,
                nabkade_category = EXCLUDED.nabkade_category,
                nabkade_brand = EXCLUDED.nabkade_brand,
                nabkade_price = EXCLUDED.nabkade_price,
                canonical_sku = EXCLUDED.canonical_sku,
                normalized_category = EXCLUDED.normalized_category,
                preferred_torob_id = EXCLUDED.preferred_torob_id,
                preferred_torob_url = EXCLUDED.preferred_torob_url,
                preferred_torob_title = EXCLUDED.preferred_torob_title,
                all_torob_ids = EXCLUDED.all_torob_ids,
                match_count = EXCLUDED.match_count,
                confidence_score = EXCLUDED.confidence_score,
                confidence_level = EXCLUDED.confidence_level,
                match_method = EXCLUDED.match_method,
                status = EXCLUDED.status,
                review_state = EXCLUDED.review_state,
                updated_at = EXCLUDED.updated_at
            """,
            (
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
            ),
        )
        self.conn.commit()
        cur.close()

    def insert_candidates(self, nabkade_id: str, scored: list) -> None:
        now = _now()
        cur = self.conn.cursor()
        for rank, s in enumerate(scored, 1):
            cur.execute(
                """
                INSERT INTO match_candidates (
                    nabkade_product_id, torob_product_id, score,
                    signals, match_source, rank, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (nabkade_id, s.torob_product_id, s.score,
                 json.dumps(s.signals), s.match_source, rank, now),
            )
        self.conn.commit()
        cur.close()

    def insert_review(self, nabkade, confidence, candidates_text: str) -> None:
        now = _now()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO review_queue (
                nabkade_product_id, nabkade_title, nabkade_url,
                nabkade_price, candidate_list, confidence_score,
                confidence_level, review_reason, status, created_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s)
            """,
            (nabkade.product_id, nabkade.title, nabkade.product_url,
             nabkade.price, candidates_text, confidence.score,
             confidence.level.value, confidence.reason, now),
        )
        self.conn.commit()
        cur.close()

    def log(self, nabkade_id: str, action: str, details: str = "") -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO matching_logs (nabkade_product_id, action, details, timestamp) VALUES (%s,%s,%s,%s)",
            (nabkade_id, action, details, _now()),
        )
        self.conn.commit()
        cur.close()

    def get_stats(self) -> dict:
        cur = sync.dict_cursor(self.conn)
        stats: dict = {}
        cur.execute("SELECT COUNT(*) AS c FROM watch_list")
        stats["total"] = cur.fetchone()["c"]

        cur.execute("SELECT confidence_level, COUNT(*) AS c FROM watch_list GROUP BY confidence_level")
        for r in cur.fetchall():
            stats[f"confidence_{r['confidence_level']}"] = r["c"]

        cur.execute("SELECT status, COUNT(*) AS c FROM watch_list GROUP BY status")
        for r in cur.fetchall():
            stats[f"status_{r['status']}"] = r["c"]

        cur.execute("SELECT COUNT(*) AS c FROM review_queue WHERE status='pending'")
        stats["review_pending"] = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) AS c FROM match_candidates")
        stats["total_candidates"] = cur.fetchone()["c"]
        cur.close()
        return stats

    def get_watch_list(self) -> list[dict]:
        cur = sync.dict_cursor(self.conn)
        cur.execute("SELECT * FROM watch_list ORDER BY confidence_level, nabkade_product_id")
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]

    def get_review_queue(self) -> list[dict]:
        cur = sync.dict_cursor(self.conn)
        cur.execute(
            "SELECT * FROM review_queue WHERE status='pending' ORDER BY confidence_score ASC"
        )
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass