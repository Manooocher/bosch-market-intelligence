"""PostgreSQL-backed store for market monitoring data.

Replaces the former SQLite implementation. Writes directly to the same tables
(db.models) the FastAPI reads: monitor_runs, market_snapshot, seller_snapshot,
latest_prices, product_status, monitor_log. The watch list is also read from
Postgres (watch_list). No bridge/ETL required.
"""

import logging
from datetime import datetime, timezone

from db import sync

logger = logging.getLogger(__name__)


def _dt(value):
    """Coerce ISO string / datetime / None into a tz-aware datetime or None."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MonitorDB:
    """PostgreSQL repository for market monitoring data."""

    def __init__(self, db_path=None):
        # db_path kept for backward-compat signature; ignored (Postgres now).
        sync.ensure_schema()
        self.conn = sync.connect()

    def _now(self) -> datetime:
        return _now()

    # ── Monitor Runs ────────────────────────────────────────────────────
    def start_run(self) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO monitor_runs (started_at, status) VALUES (%s, 'running') RETURNING id",
            (_now(),),
        )
        run_id = cur.fetchone()[0]
        self.conn.commit()
        cur.close()
        return run_id

    def finish_run(self, run_id: int, stats: dict):
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE monitor_runs SET
                finished_at = %s,
                products_total = %s,
                products_succeeded = %s,
                products_failed = %s,
                exchange_rate_rial = %s,
                exchange_rate_source = %s,
                duration_ms = %s,
                status = 'completed'
            WHERE id = %s
            """,
            (
                _now(),
                stats.get("total", 0),
                stats.get("succeeded", 0),
                stats.get("failed", 0),
                stats.get("exchange_rate", 0),
                stats.get("exchange_rate_source", ""),
                stats.get("duration_ms", 0),
                run_id,
            ),
        )
        self.conn.commit()
        cur.close()

    # ── Market Snapshots ────────────────────────────────────────────────
    def insert_snapshot(self, run_id: int, data: dict) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO market_snapshot (
                monitor_run_id, nabkade_product_id, torob_product_id,
                sku, title, category,
                seller_count, min_price_rial, max_price_rial,
                avg_price_rial, median_price_rial,
                min_price_usd, max_price_usd,
                avg_price_usd, median_price_usd,
                competition_score, price_compression, price_dispersion,
                price_spread, fetched_at,
                source_method, total_sellers_raw, in_stock_count
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                run_id,
                data.get("nabkade_product_id", ""),
                data.get("torob_product_id", ""),
                data.get("sku", ""),
                data.get("title", ""),
                data.get("category", ""),
                data.get("seller_count", 0),
                data.get("min_price_rial", 0),
                data.get("max_price_rial", 0),
                data.get("avg_price_rial", 0),
                data.get("median_price_rial", 0),
                data.get("min_price_usd", 0),
                data.get("max_price_usd", 0),
                data.get("avg_price_usd", 0),
                data.get("median_price_usd", 0),
                data.get("competition_score", 0),
                data.get("price_compression", 0.0),
                data.get("price_dispersion", 0.0),
                data.get("price_spread", 0),
                _dt(data.get("fetched_at")) or _now(),
                data.get("source_method", "details_api"),
                data.get("total_sellers_raw", 0),
                data.get("in_stock_count", 0),
            ),
        )
        snap_id = cur.fetchone()[0]
        self.conn.commit()
        cur.close()
        return snap_id

    def insert_sellers(self, snapshot_id: int, sellers: list[dict]):
        cur = self.conn.cursor()
        try:
            for s in sellers:
                cur.execute(
                    """
                    INSERT INTO seller_snapshot (
                        market_snapshot_id, seller_id, seller_name,
                        price_rial, original_price_rial, has_discount,
                        is_in_stock, shipping_cost, offer_url,
                        seller_score, seller_city, warranty_info,
                        is_promoted, extra_info_json
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        snapshot_id,
                        s.get("seller_id", ""),
                        s.get("seller_name", ""),
                        s.get("price_rial", 0),
                        s.get("original_price_rial", 0),
                        bool(s.get("has_discount", False)),
                        bool(s.get("in_stock", True)),
                        s.get("shipping_cost", 0),
                        s.get("offer_url", ""),
                        s.get("seller_score", 0),
                        s.get("seller_city", ""),
                        s.get("warranty_info", ""),
                        bool(s.get("is_promoted", False)),
                        # extra_info_json is JSONB; an empty string is invalid JSON.
                        # Coerce "" -> NULL (JSONB accepts NULL).
                        s.get("extra_info_json") or None,
                    ),
                )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    # ── Latest Prices (upsert) ─────────────────────────────────────────
    def upsert_latest(self, data: dict):
        fetched_at = _dt(data.get("fetched_at")) or _now()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO latest_prices (
                nabkade_product_id, torob_product_id, sku, title,
                category, last_fetched_at, seller_count,
                min_price_rial, max_price_rial,
                avg_price_rial, median_price_rial,
                min_price_usd, max_price_usd,
                avg_price_usd, median_price_usd,
                competition_score, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (nabkade_product_id) DO UPDATE SET
                torob_product_id = EXCLUDED.torob_product_id,
                sku = EXCLUDED.sku, title = EXCLUDED.title,
                category = EXCLUDED.category,
                last_fetched_at = EXCLUDED.last_fetched_at,
                seller_count = EXCLUDED.seller_count,
                min_price_rial = EXCLUDED.min_price_rial,
                max_price_rial = EXCLUDED.max_price_rial,
                avg_price_rial = EXCLUDED.avg_price_rial,
                median_price_rial = EXCLUDED.median_price_rial,
                min_price_usd = EXCLUDED.min_price_usd,
                max_price_usd = EXCLUDED.max_price_usd,
                avg_price_usd = EXCLUDED.avg_price_usd,
                median_price_usd = EXCLUDED.median_price_usd,
                competition_score = EXCLUDED.competition_score,
                updated_at = EXCLUDED.updated_at
            """,
            (
                data.get("nabkade_product_id", ""),
                data.get("torob_product_id", ""),
                data.get("sku", ""),
                data.get("title", ""),
                data.get("category"),
                fetched_at,
                data.get("seller_count", 0),
                data.get("min_price_rial", 0),
                data.get("max_price_rial", 0),
                data.get("avg_price_rial", 0),
                data.get("median_price_rial", 0),
                data.get("min_price_usd", 0),
                data.get("max_price_usd", 0),
                data.get("avg_price_usd", 0),
                data.get("median_price_usd", 0),
                data.get("competition_score", 0),
                _now(),
            ),
        )
        self.conn.commit()
        cur.close()

    # ── Product Status ──────────────────────────────────────────────────
    def upsert_product_status(self, torob_id: str, status: str, error_detail: str = ""):
        now = _now()
        last_fetch = now if status == "active" else None
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO product_status (torob_product_id, status, detected_at, last_successful_fetch, error_detail)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (torob_product_id) DO UPDATE SET
                status = EXCLUDED.status,
                last_successful_fetch = EXCLUDED.last_successful_fetch,
                error_detail = EXCLUDED.error_detail
            """,
            (torob_id, status, now, last_fetch, error_detail),
        )
        self.conn.commit()
        cur.close()

    def get_product_status(self, torob_id: str) -> str | None:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT status FROM product_status WHERE torob_product_id = %s", (torob_id,)
        )
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None

    # ── Monitor Log ─────────────────────────────────────────────────────
    def log_event(self, run_id: int, nabkade_id: str, event: str, detail: str = ""):
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO monitor_log (monitor_run_id, nabkade_product_id, event, detail, timestamp)
               VALUES (%s, %s, %s, %s, %s)""",
            (run_id, nabkade_id, event, detail, _now()),
        )
        self.conn.commit()
        cur.close()

    # ── Queries ─────────────────────────────────────────────────────────
    def get_watch_list(self, db_path: str = None) -> list[dict]:
        """Read matched Watch List from Postgres (watch_list)."""
        cur = sync.dict_cursor(self.conn)
        cur.execute(
            """
            SELECT id, nabkade_product_id, nabkade_title, nabkade_url,
                   nabkade_price, canonical_sku, normalized_category,
                   preferred_torob_id, preferred_torob_url, preferred_torob_title,
                   confidence_level, match_count
            FROM watch_list
            WHERE status = 'matched'
              AND confidence_level IN ('high', 'medium')
            """,
        )
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]

    def get_exchange_rate_history(self, limit: int = 10) -> list[dict]:
        cur = sync.dict_cursor(self.conn)
        cur.execute(
            """
            SELECT exchange_rate_rial, exchange_rate_source, finished_at
            FROM monitor_runs
            WHERE exchange_rate_rial > 0
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {"rate": r["exchange_rate_rial"], "source": r["exchange_rate_source"],
             "timestamp": r["finished_at"]} for r in rows
        ]

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass