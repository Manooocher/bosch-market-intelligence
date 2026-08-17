"""Daily Market Monitor — main pipeline.

Reads Watch List → Fetches Torob product details → Parses sellers →
Calculates statistics → Converts currency → Stores results.

V2: Uses get_product_details() directly instead of search API.
This captures the full seller list (up to 50) for accurate competition analysis.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from crawler.config import CrawlerConfig
from crawler.http_client import HttpClient, Response
from crawler.torob import TorobCrawler, CrawlerResponse
from crawler.scheduler import RequestScheduler, WorkItem
from crawler.circuit_breaker import CircuitBreaker
from crawler.metrics import MetricsCollector
from crawler.currency import ExchangeRateFetcher, RialRate, toman_to_usd_cents
from crawler.statistics import compute_market_stats, MarketStats, filter_outlier_prices
from crawler.seller_parser import parse_sellers_v2, SellerParseResult
from crawler.monitor_db import MonitorDB

logger = logging.getLogger(__name__)


@dataclass
class ProductMarketData:
    """Collected market data for one product."""
    nabkade_product_id: str
    torob_product_id: str
    sku: str
    title: str
    category: str
    seller_count: int = 0
    min_price_rial: int = 0
    max_price_rial: int = 0
    avg_price_rial: int = 0
    median_price_rial: int = 0
    min_price_usd: int = 0
    max_price_usd: int = 0
    avg_price_usd: int = 0
    median_price_usd: int = 0
    competition_score: int = 0
    price_compression: float = 0.0
    price_dispersion: float = 0.0
    price_spread: int = 0
    fetched_at: str = ""
    success: bool = False
    error: str = ""
    sellers: list[dict] = field(default_factory=list)
    # ── New fields ──
    source_method: str = "details_api"
    total_sellers_raw: int = 0
    in_stock_count: int = 0


class DailyMonitor:
    """Production daily monitor for Watch List products.

    Pipeline (V2 — Details API):
    1. Load Watch List from matcher DB
    2. For each product: get_product_details(torob_id)
    3. Parse full seller array (up to 50 sellers)
    4. Compute market statistics (in-stock sellers only)
    5. Convert to USD
    6. Store results in monitor DB
    """

    def __init__(
        self,
        crawler: TorobCrawler,
        scheduler: RequestScheduler,
        exchange_rate: ExchangeRateFetcher,
        monitor_db: MonitorDB,
        metrics: MetricsCollector,
        config: CrawlerConfig,
    ):
        self.crawler = crawler
        self.scheduler = scheduler
        self.exchange_rate = exchange_rate
        self.db = monitor_db
        self.metrics = metrics
        self.config = config
        self._run_id: int | None = None
        self._product_failures: dict = {}      # torob_id → consecutive failure count
        self._global_consecutive_failures: int = 0

    def run(self) -> dict:
        """Execute the full monitoring pipeline. Returns summary."""
        start_time = time.time()
        logger.info("=== Daily Market Monitor Started (V2 — Details API) ===")

        # 1. Create run
        self._run_id = self.db.start_run()
        logger.info(f"Monitor run #{self._run_id} started")

        try:
            # 2. Fetch exchange rate
            rate = self.exchange_rate.fetch()
            logger.info(f"Exchange rate: {rate.value} IRR/USDT ({rate.source})")

            # 3. Load Watch List
            watch_list = self.db.get_watch_list()
            if not watch_list:
                logger.error("Watch List is empty — aborting")
                self._finish_run(start_time, {"total": 0, "succeeded": 0, "failed": 0,
                                                "exchange_rate": rate.value,
                                                "exchange_rate_source": rate.source})
                return {"total": 0, "succeeded": 0, "failed": 0}

            logger.info(f"Loaded {len(watch_list)} products from Watch List")

            # 4. Process in batches
            batches = self.scheduler.create_batches(watch_list)
            total_succeeded = 0
            total_failed = 0

            for batch_idx, batch in enumerate(batches):
                logger.info(f"Processing batch {batch_idx + 1}/{len(batches)} ({len(batch)} products)")
                batch_start = time.time()
                batch_succeeded = 0

                for item in batch:
                    # Delay between items (4-6s)
                    delay = self.scheduler.get_delay()
                    time.sleep(delay)

                    # Check circuit breaker
                    if not self.crawler.client.circuit_breaker.allow_request():
                        logger.warning("Circuit breaker open — pausing batch")
                        time.sleep(120)
                        self.crawler.client.circuit_breaker.reset()

                    # Check global consecutive failure circuit breaker
                    if self._global_consecutive_failures >= 5:
                        logger.critical("5 global consecutive failures — halting execution")
                        break

                    # Fetch and process (details API)
                    market_data = self._process_product(item, rate)
                    if market_data.success:
                        total_succeeded += 1
                        batch_succeeded += 1
                        self._store_product_data(market_data)
                        self._global_consecutive_failures = 0
                    else:
                        total_failed += 1
                        torob_id = item.get("preferred_torob_id", "")
                        self._product_failures[torob_id] = self._product_failures.get(torob_id, 0) + 1
                        self._global_consecutive_failures += 1

                        self.db.log_event(
                            self._run_id,
                            item.get("nabkade_product_id", ""),
                            "fetch_failed",
                            market_data.error,
                        )

                    self.scheduler.on_item_complete(market_data.success)

                # Batch complete
                batch_duration = int((time.time() - batch_start) * 1000)
                self.scheduler.on_batch_complete(len(batch), batch_succeeded, batch_duration)

                # Rotate proxy if needed
                if self.scheduler.should_rotate():
                    self.crawler.client.proxy_manager.rotate(reason="batch_boundary")
                    self.crawler.client.fingerprint.rotate_identity()
                    self.crawler.client._setup_session()
                    self.metrics.record_proxy_rotation("batch_boundary")

                # Pause between batches
                pause = self.scheduler.get_batch_pause()
                logger.info(f"Batch pause: {pause:.1f}s")
                time.sleep(pause)

                # Check global halt
                if self._global_consecutive_failures >= 5:
                    logger.critical("Global circuit breaker tripped — halting monitor")
                    break

            # 5. Finish
            duration_ms = int((time.time() - start_time) * 1000)
            summary = {
                "total": len(watch_list),
                "succeeded": total_succeeded,
                "failed": total_failed,
                "exchange_rate": rate.value,
                "exchange_rate_source": rate.source,
                "duration_ms": duration_ms,
            }

            self._finish_run(start_time, summary)
            self.metrics.write_final_summary("monitor")

            logger.info(f"=== Monitor Complete: {total_succeeded}/{len(watch_list)} succeeded "
                         f"in {duration_ms / 1000:.1f}s ===")

            return summary

        except KeyboardInterrupt:
            logger.info("Monitor interrupted by user")
            duration_ms = int((time.time() - start_time) * 1000)
            self._finish_run(start_time, {"total": 0, "succeeded": 0, "failed": 0,
                                           "duration_ms": duration_ms, "status": "interrupted"})
            return {"total": 0, "succeeded": 0, "failed": 0, "status": "interrupted"}

        except Exception as e:
            logger.error(f"Monitor failed: {e}", exc_info=True)
            duration_ms = int((time.time() - start_time) * 1000)
            self._finish_run(start_time, {"total": 0, "succeeded": 0, "failed": 0,
                                           "duration_ms": duration_ms, "status": "error",
                                           "error": str(e)})
            raise

    def _process_product(self, item: dict, rate: RialRate) -> ProductMarketData:
        """Fetch product sellers from Torob and compute stats.

        V3: Uses get_sellers() endpoint — NO search API, NO details API.
        The sellers endpoint returns the full seller list (up to 40+ sellers).
        Filters out-of-stock sellers from price statistics.
        """
        nabkade_id = item.get("nabkade_product_id", "")
        torob_id = item.get("preferred_torob_id", "")
        sku = item.get("canonical_sku", "")
        title = item.get("nabkade_title", "")
        category = item.get("normalized_category", "")

        now = datetime.now(timezone.utc).isoformat()
        product_data = ProductMarketData(
            nabkade_product_id=nabkade_id,
            torob_product_id=torob_id,
            sku=sku,
            title=title,
            category=category,
            fetched_at=now,
            source_method="sellers_api",
        )

        try:
            # ── Fetch sellers via dedicated sellers endpoint ──
            sellers_response = self.crawler.get_sellers(torob_id)

            if not sellers_response.success:
                if sellers_response.status_code == 404:
                    product_data.error = "product_deleted"
                    self.db.upsert_product_status(torob_id, "deleted")
                    return product_data
                product_data.error = sellers_response.error or "sellers_fetch_failed"
                return product_data

            sellers_data = sellers_response.data
            if not sellers_data:
                product_data.error = "empty_sellers_response"
                return product_data

            # Extract sellers array from response
            sellers_list = sellers_data.get("results", []) if isinstance(sellers_data, dict) else sellers_data
            if not isinstance(sellers_list, list):
                product_data.error = "invalid_sellers_format"
                return product_data

            # ── Parse sellers ──
            seller_result = parse_sellers_v2({"sellers": sellers_list, "name1": title}, torob_id)

            # Update product status
            if not seller_result.sellers:
                self.db.upsert_product_status(torob_id, "no_sellers")
            else:
                self.db.upsert_product_status(torob_id, "active")

            # Total sellers returned by API
            product_data.total_sellers_raw = len(seller_result.sellers)

            # Filter to in_stock sellers ONLY for statistics
            in_stock_sellers = [s for s in seller_result.sellers if s.in_stock]
            product_data.in_stock_count = len(in_stock_sellers)

            if not in_stock_sellers:
                product_data.error = "no_in_stock_sellers"
                product_data.seller_count = 0
                product_data.success = True
                product_data.sellers = []
                return product_data

            # Extract prices from in_stock sellers only, dropping low outliers
            prices_rial = [s.price_rial for s in in_stock_sellers if s.price_rial > 0]
            if not prices_rial:
                product_data.error = "no_valid_prices_in_stock"
                return product_data
            prices_rial = filter_outlier_prices(prices_rial)

            # Compute market statistics
            stats = compute_market_stats(prices_rial)

            product_data.seller_count = len(in_stock_sellers)
            product_data.min_price_rial = stats.min_price
            product_data.max_price_rial = stats.max_price
            product_data.avg_price_rial = stats.avg_price
            product_data.median_price_rial = stats.median_price
            product_data.price_spread = stats.price_spread
            product_data.price_compression = stats.price_compression
            product_data.price_dispersion = stats.price_dispersion
            product_data.competition_score = stats.competition_score

            product_data.min_price_usd = toman_to_usd_cents(stats.min_price, rate.value)
            product_data.max_price_usd = toman_to_usd_cents(stats.max_price, rate.value)
            product_data.avg_price_usd = toman_to_usd_cents(stats.avg_price, rate.value)
            product_data.median_price_usd = toman_to_usd_cents(stats.median_price, rate.value)

            # Store ALL sellers (including out_of_stock) for complete record
            product_data.sellers = [
                {
                    "seller_id": s.seller_id,
                    "seller_name": s.seller_name,
                    "price_rial": s.price_rial,
                    "seller_score": s.seller_score,
                    "seller_city": s.seller_city,
                    "warranty_info": s.warranty_info,
                    "is_promoted": s.is_promoted,
                    "extra_info_json": s.extra_info_json,
                    "original_price_rial": s.original_price_rial,
                    "has_discount": s.has_discount,
                    "in_stock": s.in_stock,
                    "shipping_cost": s.shipping_cost,
                    "offer_url": s.offer_url,
                }
                for s in seller_result.sellers
            ]

            product_data.success = True
            return product_data

        except Exception as e:
            logger.warning(f"Failed to process {nabkade_id}: {e}")
            product_data.error = str(e)
            return product_data

    def _store_product_data(self, data: ProductMarketData):
        """Store computed market data in the monitor database."""
        snapshot_data = {
            "nabkade_product_id": data.nabkade_product_id,
            "torob_product_id": data.torob_product_id,
            "sku": data.sku,
            "title": data.title,
            "category": data.category,
            "seller_count": data.seller_count,
            "min_price_rial": data.min_price_rial,
            "max_price_rial": data.max_price_rial,
            "avg_price_rial": data.avg_price_rial,
            "median_price_rial": data.median_price_rial,
            "min_price_usd": data.min_price_usd,
            "max_price_usd": data.max_price_usd,
            "avg_price_usd": data.avg_price_usd,
            "median_price_usd": data.median_price_usd,
            "competition_score": data.competition_score,
            "price_compression": data.price_compression,
            "price_dispersion": data.price_dispersion,
            "price_spread": data.price_spread,
            "source_method": data.source_method,
            "total_sellers_raw": data.total_sellers_raw,
            "in_stock_count": data.in_stock_count,
        }

        snapshot_id = self.db.insert_snapshot(self._run_id, snapshot_data)

        if data.sellers:
            self.db.insert_sellers(snapshot_id, data.sellers)

        self.db.upsert_latest(snapshot_data)

    def _finish_run(self, start_time: float, stats: dict):
        """Mark the run as completed."""
        stats["duration_ms"] = int((time.time() - start_time) * 1000)
        if self._run_id:
            self.db.finish_run(self._run_id, stats)
