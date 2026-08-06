"""CLI entry point for Daily Market Monitor — Production Version.

Usage:
    python -m cli.monitor

Requires .env file with proxy and Tabdeal configuration.
"""

import atexit
import logging
import signal
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger("cli.monitor")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from crawler.production import (
        validate_startup, ExecutionLock, BackupManager,
        HealthChecker, setup_production_logging, StartupValidationError,
    )
    from crawler.config import CrawlerConfig
    from crawler.fingerprint import FingerprintManager
    from crawler.proxy import ProxyManager
    from crawler.proxy_health import ProxyHealthStore
    from crawler.circuit_breaker import CircuitBreaker
    from crawler.retry import RetryPolicy
    from crawler.metrics import MetricsCollector
    from crawler.scheduler import RequestScheduler
    from crawler.http_client import HttpClient
    from crawler.torob import TorobCrawler
    from crawler.currency import ExchangeRateFetcher
    from crawler.monitor_db import MonitorDB
    from crawler.monitor import DailyMonitor

    # ── 1. Setup production logging ─────────────────────────────────────
    setup_production_logging()

    # ── 2. Startup validation ──────────────────────────────────────────
    logger.info("Running startup validation...")
    try:
        validate_startup()
    except StartupValidationError as e:
        logger.critical(f"Startup validation FAILED: {e}")
        return 2

    logger.info("Startup validation PASSED")

    # ── 3. Acquire execution lock ──────────────────────────────────────
    lock = ExecutionLock()
    if not lock.acquire():
        logger.critical("Another monitor instance is already running")
        logger.critical("If this is an error, delete data/.monitor.lock")
        return 3

    # ── 4. Create backup ───────────────────────────────────────────────
    logger.info("Creating pre-run backups...")
    backup = BackupManager()
    for db_name in ["watch_list.db", "monitor_store.db", "proxy_health.db"]:
        db_path = f"data/{db_name}"
        if os.path.exists(db_path):
            backup.create_backup(db_path, name=db_name)
    backup.cleanup_old_backups()

    # ── 5. Initialize infrastructure ───────────────────────────────────
    logger.info("Initializing infrastructure...")
    config = CrawlerConfig.from_env()
    rate_profile = config.get_rate_profile("monitor")

    health_store = ProxyHealthStore()
    proxy_manager = ProxyManager(config.proxy, health_store)
    fingerprint = FingerprintManager()
    circuit_breaker = CircuitBreaker(config.circuit_breaker)
    retry_policy = RetryPolicy(config.retry)
    metrics = MetricsCollector()
    scheduler = RequestScheduler(rate_profile, proxy_manager, config.scheduler)

    http_client = HttpClient(
        config=config,
        proxy_manager=proxy_manager,
        fingerprint=fingerprint,
        circuit_breaker=circuit_breaker,
        retry_policy=retry_policy,
        metrics=metrics,
        mode="monitor",
    )

    crawler = TorobCrawler(http_client, config)
    exchange_rate = ExchangeRateFetcher(http_client)
    monitor_db = MonitorDB()

    # Register shutdown handler
    def shutdown():
        logger.info("Shutdown: closing resources...")
        http_client.close()
        health_store.close()
        monitor_db.close()
        lock.release()

    atexit.register(shutdown)

    # Handle signals
    def signal_handler(signum, frame):
        logger.info(f"Signal {signum} received, shutting down...")
        shutdown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # ── 6. Run monitor ─────────────────────────────────────────────────
    monitor = DailyMonitor(
        crawler=crawler,
        scheduler=scheduler,
        exchange_rate=exchange_rate,
        monitor_db=monitor_db,
        metrics=metrics,
        config=config,
    )

    exit_code = 0
    try:
        summary = monitor.run()
        logger.info(f"Monitor completed: {summary}")

        # Write final metrics
        metrics.write_to_file()
        metrics.write_final_summary("monitor")

    except KeyboardInterrupt:
        logger.info("Monitor interrupted by user")
        exit_code = 0

    except Exception as e:
        logger.error(f"Monitor failed: {e}", exc_info=True)
        exit_code = 1

    finally:
        shutdown()

    logger.info(f"Exit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
