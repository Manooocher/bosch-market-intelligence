"""CLI entry point for Catalog Bootstrap — Production Version.

Usage:
    python -m cli.bootstrap

Runs recovery → patch catalog → rebuild matcher → regenerate Watch List.
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from crawler.production import (
        validate_startup, ExecutionLock, BackupManager,
        setup_production_logging, StartupValidationError,
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
    from crawler.bootstrap import Bootstrap

    # ── Setup production logging ────────────────────────────────────────
    setup_production_logging()
    logger = logging.getLogger("cli.bootstrap")

    # ── Startup validation ─────────────────────────────────────────────
    logger.info("Running startup validation...")
    try:
        validate_startup()
    except StartupValidationError as e:
        logger.critical(f"Startup validation FAILED: {e}")
        return 2
    logger.info("Startup validation PASSED")

    # ── Acquire execution lock ─────────────────────────────────────────
    lock = ExecutionLock()
    if not lock.acquire():
        logger.critical("Another bootstrap instance is already running")
        return 3

    # ── Create backup ──────────────────────────────────────────────────
    logger.info("Creating pre-run backups...")
    backup = BackupManager()
    for db_name in ["watch_list.db", "torob.sqlite3"]:
        db_path = f"data/{db_name}"
        if os.path.exists(db_path):
            backup.create_backup(db_path, name=db_name)

    # ── Initialize infrastructure ──────────────────────────────────────
    logger.info("Initializing infrastructure...")
    config = CrawlerConfig.from_env()
    rate_profile = config.get_rate_profile("recovery")

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
        mode="recovery",
    )

    crawler = TorobCrawler(http_client, config)
    bootstrap = Bootstrap(crawler=crawler)

    # Register shutdown handler
    def shutdown():
        logger.info("Shutdown: closing resources...")
        http_client.close()
        health_store.close()
        lock.release()

    import atexit
    atexit.register(shutdown)

    # ── Run bootstrap ──────────────────────────────────────────────────
    exit_code = 0
    try:
        result = bootstrap.run()
        logger.info(f"Bootstrap result: {json.dumps(result.__dict__, indent=2, default=str)}")

        diag_summary = proxy_manager.get_diagnostic_summary()
        if diag_summary.get("total", 0) > 0:
            logger.info(f"Proxy diagnostics: {json.dumps(diag_summary, indent=2, default=str)}")

    except KeyboardInterrupt:
        logger.info("Bootstrap interrupted by user")
        exit_code = 0

    except Exception as e:
        logger.error(f"Bootstrap failed: {e}", exc_info=True)
        exit_code = 1

    finally:
        shutdown()

    logger.info(f"Exit code: {exit_code}")
    return exit_code


import os

if __name__ == "__main__":
    sys.exit(main())
