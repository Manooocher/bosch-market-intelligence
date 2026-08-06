"""Daily Market Monitor — main pipeline.

Reads Watch List → Fetches Torob data → Parses sellers →
Calculates statistics → Converts currency → Stores results.
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
from crawler.statistics import compute_market_stats, MarketStats
from crawler.seller_parser import parse_sellers, SellerParseResult
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


class DailyMonitor:
    """Production daily monitor for Watch List products.

    Pipeline:
    1. Load Watch List from matcher DB
    2. For each product: fetch Torob data, parse sellers, compute stats, convert USD
    3. Store results in monitor DB
    4. Update latest_prices for client API
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

    def run(self) -> dict:
        """Execute the full monitoring pipeline. Returns summary."""
        start_time = time.time()
        logger.info("=== Daily Market Monitor Started ===")

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
                    # Delay between items
                    delay = self.scheduler.get_delay()
                    time.sleep(delay)

                    # Check circuit breaker
                    if not self.crawler.client.circuit_breaker.allow_request():
                        logger.warning("Circuit breaker open — pausing batch")
                        time.sleep(120)
                        self.crawler.client.circuit_breaker.reset()

                    # Fetch and process
                    market_data = self._process_product(item, rate)
                    if market_data.success:
                        total_succeeded += 1
                        batch_succeeded += 1
                        self._store_product_data(market_data)
                    else:
                        total_failed += 1
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
                time.sleep(pause)

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
        """Fetch Torob data and compute stats for one product."""
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
        )

        try:
            # Fetch product details from Torob
            response = self.crawler.search(query=sku or title, brand=73)

            if not response.success or not response.data:
                product_data.error = response.error or "empty_response"
                return product_data

            # Find our product in results
            results = response.data.get("results", [])
            torob_product = None

            for r in results:
                r_id = r.get("random_key", "")
                if r_id == torob_id:
                    torob_product = r
                    break
                # Fallback: check if title matches
                r_title = r.get("name1", "")
                if sku and sku.lower() in r_title.lower():
                    torob_product = r
                    break

            if not torob_product:
                # Try details endpoint
                detail_response = self.crawler.get_product_details(torob_id)
                if detail_response.success and detail_response.data:
                    torob_product = detail_response.data

            if not torob_product:
                product_data.error = "product_not_found"
                return product_data

            # Parse sellers
            seller_result = parse_sellers(torob_product, torob_id)

            if not seller_result.sellers:
                # Check if product itself has price (single-seller)
                single_price = torob_product.get("price", 0)
                if single_price and int(single_price) > 0:
                    from crawler.seller_parser import Seller
                    seller_result.sellers = [Seller(
                        seller_id="direct",
                        seller_name="Torob",
                        price_rial=int(single_price),
                    )]

            if not seller_result.sellers:
                product_data.error = "no_sellers"
                return product_data

            # Extract prices
            prices_rial = [s.price_rial for s in seller_result.sellers if s.price_rial > 0]

            if not prices_rial:
                product_data.error = "no_valid_prices"
                return product_data

            # Compute market statistics
            stats = compute_market_stats(prices_rial)

            # Convert to USD
            product_data.seller_count = stats.seller_count
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

            # Store seller data
            product_data.sellers = [
                {
                    "seller_id": s.seller_id,
                    "seller_name": s.seller_name,
                    "price_rial": s.price_rial,
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
            "fetched_at": data.fetched_at,
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
