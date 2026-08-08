"""SQLite database for market monitoring.

Creates and manages tables for price snapshots, seller data, and monitor runs.
Does not touch the Watch List database — reads it via SQL.
"""

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from crawler.config import DATA_DIR

logger = logging.getLogger(__name__)

MONITOR_DB_PATH = DATA_DIR / "monitor_store.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS monitor_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    products_total INTEGER DEFAULT 0,
    products_succeeded INTEGER DEFAULT 0,
    products_failed INTEGER DEFAULT 0,
    exchange_rate_rial INTEGER DEFAULT 0,
    exchange_rate_source TEXT DEFAULT '',
    duration_ms INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS market_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_run_id INTEGER NOT NULL,
    nabkade_product_id TEXT NOT NULL,
    torob_product_id TEXT NOT NULL,
    sku TEXT,
    title TEXT,
    category TEXT,
    seller_count INTEGER DEFAULT 0,
    min_price_rial INTEGER DEFAULT 0,
    max_price_rial INTEGER DEFAULT 0,
    avg_price_rial INTEGER DEFAULT 0,
    median_price_rial INTEGER DEFAULT 0,
    min_price_usd INTEGER DEFAULT 0,
    max_price_usd INTEGER DEFAULT 0,
    avg_price_usd INTEGER DEFAULT 0,
    median_price_usd INTEGER DEFAULT 0,
    competition_score INTEGER DEFAULT 0,
    price_compression REAL DEFAULT 0.0,
    price_dispersion REAL DEFAULT 0.0,
    price_spread INTEGER DEFAULT 0,
    fetched_at TEXT NOT NULL,
    source_method TEXT DEFAULT 'details_api',
    total_sellers_raw INTEGER DEFAULT 0,
    in_stock_count INTEGER DEFAULT 0,
    FOREIGN KEY (monitor_run_id) REFERENCES monitor_runs(id)
);

CREATE TABLE IF NOT EXISTS seller_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_snapshot_id INTEGER NOT NULL,
    seller_id TEXT NOT NULL,
    seller_name TEXT,
    price_rial INTEGER DEFAULT 0,
    original_price_rial INTEGER DEFAULT 0,
    has_discount INTEGER DEFAULT 0,
    in_stock INTEGER DEFAULT 1,
    shipping_cost INTEGER DEFAULT 0,
    offer_url TEXT,
    seller_score INTEGER DEFAULT 0,
    seller_city TEXT DEFAULT '',
    warranty_info TEXT DEFAULT '',
    is_promoted INTEGER DEFAULT 0,
    extra_info_json TEXT DEFAULT '',
    FOREIGN KEY (market_snapshot_id) REFERENCES market_snapshot(id)
);

CREATE TABLE IF NOT EXISTS latest_prices (
    nabkade_product_id TEXT PRIMARY KEY,
    torob_product_id TEXT NOT NULL,
    sku TEXT,
    title TEXT,
    last_fetched_at TEXT,
    seller_count INTEGER DEFAULT 0,
    min_price_rial INTEGER DEFAULT 0,
    max_price_rial INTEGER DEFAULT 0,
    avg_price_rial INTEGER DEFAULT 0,
    median_price_rial INTEGER DEFAULT 0,
    min_price_usd INTEGER DEFAULT 0,
    max_price_usd INTEGER DEFAULT 0,
    avg_price_usd INTEGER DEFAULT 0,
    median_price_usd INTEGER DEFAULT 0,
    competition_score INTEGER DEFAULT 0,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS monitor_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_run_id INTEGER,
    nabkade_product_id TEXT,
    event TEXT,
    detail TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (monitor_run_id) REFERENCES monitor_runs(id)
);

CREATE TABLE IF NOT EXISTS product_status (
    torob_product_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'unknown',
    detected_at TEXT,
    last_successful_fetch TEXT,
    error_detail TEXT
);

CREATE INDEX IF NOT EXISTS idx_snapshot_run ON market_snapshot(monitor_run_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_product ON market_snapshot(nabkade_product_id);
CREATE INDEX IF NOT EXISTS idx_seller_snapshot ON seller_snapshot(market_snapshot_id);
CREATE INDEX IF NOT EXISTS idx_monitor_log_run ON monitor_log(monitor_run_id);
"""


class MonitorDB:
    """SQLite store for market monitoring data."""

    def __init__(self, db_path=None):
        self.db_path = db_path or MONITOR_DB_PATH
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()
        self._migrate()

    def _create_schema(self):
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def _migrate(self):
        """Add new columns if they don't exist (safe for existing DBs)."""
        migrations = [
            ("ALTER TABLE seller_snapshot ADD COLUMN seller_score INTEGER DEFAULT 0",),
            ("ALTER TABLE seller_snapshot ADD COLUMN seller_city TEXT DEFAULT ''",),
            ("ALTER TABLE seller_snapshot ADD COLUMN warranty_info TEXT DEFAULT ''",),
            ("ALTER TABLE seller_snapshot ADD COLUMN is_promoted INTEGER DEFAULT 0",),
            ("ALTER TABLE seller_snapshot ADD COLUMN extra_info_json TEXT DEFAULT ''",),
            ("ALTER TABLE market_snapshot ADD COLUMN source_method TEXT DEFAULT 'legacy_search'",),
            ("ALTER TABLE market_snapshot ADD COLUMN total_sellers_raw INTEGER DEFAULT 0",),
            ("ALTER TABLE market_snapshot ADD COLUMN in_stock_count INTEGER DEFAULT 0",),
        ]
        for sql in migrations:
            try:
                self.conn.execute(sql[0])
            except sqlite3.OperationalError:
                pass  # Column already exists
        self.conn.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Monitor Runs ────────────────────────────────────────────────────

    def start_run(self) -> int:
        cur = self.conn.execute(
            "INSERT INTO monitor_runs (started_at, status) VALUES (?, 'running')",
            (self._now(),),
        )
        self.conn.commit()
        return cur.lastrowid

    def finish_run(self, run_id: int, stats: dict):
        self.conn.execute("""
            UPDATE monitor_runs SET
                finished_at = ?,
                products_total = ?,
                products_succeeded = ?,
                products_failed = ?,
                exchange_rate_rial = ?,
                exchange_rate_source = ?,
                duration_ms = ?,
                status = 'completed'
            WHERE id = ?
        """, (
            self._now(),
            stats.get("total", 0),
            stats.get("succeeded", 0),
            stats.get("failed", 0),
            stats.get("exchange_rate", 0),
            stats.get("exchange_rate_source", ""),
            stats.get("duration_ms", 0),
            run_id,
        ))
        self.conn.commit()

    # ── Market Snapshots ────────────────────────────────────────────────

    def insert_snapshot(self, run_id: int, data: dict) -> int:
        cur = self.conn.execute("""
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
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
            data.get("fetched_at", self._now()),
            data.get("source_method", "details_api"),
            data.get("total_sellers_raw", 0),
            data.get("in_stock_count", 0),
        ))
        self.conn.commit()
        return cur.lastrowid

    def insert_sellers(self, snapshot_id: int, sellers: list[dict]):
        for s in sellers:
            self.conn.execute("""
                INSERT INTO seller_snapshot (
                    market_snapshot_id, seller_id, seller_name,
                    price_rial, original_price_rial, has_discount,
                    in_stock, shipping_cost, offer_url,
                    seller_score, seller_city, warranty_info,
                    is_promoted, extra_info_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id,
                s.get("seller_id", ""),
                s.get("seller_name", ""),
                s.get("price_rial", 0),
                s.get("original_price_rial", 0),
                1 if s.get("has_discount", False) else 0,
                1 if s.get("in_stock", True) else 0,
                s.get("shipping_cost", 0),
                s.get("offer_url", ""),
                s.get("seller_score", 0),
                s.get("seller_city", ""),
                s.get("warranty_info", ""),
                1 if s.get("is_promoted", False) else 0,
                s.get("extra_info_json", ""),
            ))
        self.conn.commit()

    # ── Latest Prices (upsert) ─────────────────────────────────────────

    def upsert_latest(self, data: dict):
        self.conn.execute("""
            INSERT OR REPLACE INTO latest_prices (
                nabkade_product_id, torob_product_id, sku, title,
                last_fetched_at, seller_count,
                min_price_rial, max_price_rial,
                avg_price_rial, median_price_rial,
                min_price_usd, max_price_usd,
                avg_price_usd, median_price_usd,
                competition_score, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("nabkade_product_id", ""),
            data.get("torob_product_id", ""),
            data.get("sku", ""),
            data.get("title", ""),
            data.get("fetched_at", self._now()),
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
            self._now(),
        ))
        self.conn.commit()

    # ── Product Status ──────────────────────────────────────────────────

    def upsert_product_status(self, torob_id: str, status: str, error_detail: str = ""):
        now = self._now()
        last_fetch = now if status == 'active' else None
        self.conn.execute("""
            INSERT INTO product_status (torob_product_id, status, detected_at, last_successful_fetch, error_detail)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(torob_product_id) DO UPDATE SET
                status = excluded.status,
                last_successful_fetch = ?,
                error_detail = excluded.error_detail
        """, (torob_id, status, now, last_fetch, error_detail, last_fetch))
        self.conn.commit()

    def get_product_status(self, torob_id: str) -> str | None:
        row = self.conn.execute(
            "SELECT status FROM product_status WHERE torob_product_id = ?", (torob_id,)
        ).fetchone()
        return row[0] if row else None

    # ── Monitor Log ─────────────────────────────────────────────────────

    def log_event(self, run_id: int, nabkade_id: str, event: str, detail: str = ""):
        self.conn.execute("""
            INSERT INTO monitor_log (monitor_run_id, nabkade_product_id, event, detail, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (run_id, nabkade_id, event, detail, self._now()))
        self.conn.commit()

    # ── Queries ─────────────────────────────────────────────────────────

    def get_watch_list(self, db_path: str = None) -> list[dict]:
        """Read Watch List from the matcher database."""
        wl_path = db_path or str(DATA_DIR / "watch_list.db")
        if not os.path.exists(wl_path):
            logger.error(f"Watch List DB not found: {wl_path}")
            return []

        wl_conn = sqlite3.connect(wl_path)
        wl_conn.row_factory = sqlite3.Row
        rows = wl_conn.execute("""
            SELECT id, nabkade_product_id, nabkade_title, nabkade_url,
                   nabkade_price, canonical_sku, normalized_category,
                   preferred_torob_id, preferred_torob_url, preferred_torob_title,
                   confidence_level, match_count
            FROM watch_list
            WHERE status = 'matched'
            AND confidence_level IN ('high', 'medium')
        """).fetchall()
        wl_conn.close()

        return [dict(row) for row in rows]

    def get_exchange_rate_history(self, limit: int = 10) -> list[dict]:
        rows = self.conn.execute("""
            SELECT exchange_rate_rial, exchange_rate_source, finished_at
            FROM monitor_runs
            WHERE exchange_rate_rial > 0
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [{"rate": r[0], "source": r[1], "timestamp": r[2]} for r in rows]

    def close(self):
        self.conn.close()
