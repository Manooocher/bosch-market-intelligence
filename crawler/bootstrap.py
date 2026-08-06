"""Catalog Bootstrap Pipeline.

Recovery → Patch Torob Catalog → Rebuild Matcher → Regenerate Watch List.
This module runs BEFORE Daily Monitor.

Usage:
    from crawler.bootstrap import Bootstrap
    bootstrap = Bootstrap(crawler=torob_crawler)
    result = bootstrap.run()
"""

import csv
import json
import logging
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from crawler.config import DATA_DIR
from crawler.torob import TorobCrawler
from crawler.recovery import CatalogRecovery

logger = logging.getLogger(__name__)

COVERAGE_CSV = DATA_DIR / "analysis" / "catalog_coverage.csv"
TOROB_CSV = DATA_DIR / "bosch_products_links.final.csv"
TOROB_CSV_BACKUP = DATA_DIR / "bosch_products_links.backup.csv"


@dataclass
class BootstrapResult:
    """Summary of bootstrap execution."""
    missing_skus_total: int = 0
    recovered_count: int = 0
    still_missing_count: int = 0
    torob_catalog_patched: bool = False
    matcher_rebuilt: bool = False
    execution_time_ms: int = 0
    errors: list = field(default_factory=list)


class Bootstrap:
    """Recovery pipeline: ensure Watch List is complete before monitoring.

    Steps:
    1. Load catalog_coverage.csv → find missing SKUs
    2. Run CatalogRecovery via shared TorobCrawler
    3. Patch Torob catalog CSV
    4. Rebuild Matcher (indexes + Watch List)
    5. Regenerate review_queue.csv and QA reports
    """

    def __init__(self, crawler: TorobCrawler):
        self.crawler = crawler
        self.recovery = CatalogRecovery(crawler)

    def run(self) -> BootstrapResult:
        """Execute full bootstrap pipeline."""
        start = time.time()
        result = BootstrapResult()

        logger.info("=== Catalog Bootstrap Started ===")

        # Step 1: Load missing SKUs
        missing_skus = self._load_missing_skus()
        result.missing_skus_total = len(missing_skus)

        if not missing_skus:
            logger.info("No missing SKUs found. Bootstrap complete.")
            result.execution_time_ms = int((time.time() - start) * 1000)
            return result

        logger.info(f"Found {len(missing_skus)} missing SKUs to recover")

        # Step 2: Run recovery
        recovered = self.recovery.recover_missing_skus(
            missing_skus,
            on_progress=lambda i, t, s: logger.info(f"  [{i}/{t}] Searching for {s}")
        )
        result.recovered_count = len(recovered)
        result.still_missing_count = len(missing_skus) - len(recovered)

        stats = self.recovery.get_statistics()
        logger.info(f"Recovery: {stats}")

        if not recovered:
            logger.info("No products recovered. Skipping catalog patch and matcher rebuild.")
            result.execution_time_ms = int((time.time() - start) * 1000)
            return result

        # Step 3: Patch Torob catalog
        self._patch_torob_catalog(recovered)
        result.torob_catalog_patched = True

        # Step 4: Rebuild Matcher
        try:
            self._rebuild_matcher()
            result.matcher_rebuilt = True
        except Exception as e:
            logger.error(f"Matcher rebuild failed: {e}")
            result.errors.append(f"matcher_rebuild: {str(e)}")

        result.execution_time_ms = int((time.time() - start) * 1000)

        # Summary
        logger.info("=" * 60)
        logger.info("BOOTSTRAP SUMMARY")
        logger.info(f"  Missing SKUs: {result.missing_skus_total}")
        logger.info(f"  Recovered: {result.recovered_count}")
        logger.info(f"  Still Missing: {result.still_missing_count}")
        logger.info(f"  Catalog Patched: {result.torob_catalog_patched}")
        logger.info(f"  Matcher Rebuilt: {result.matcher_rebuilt}")
        logger.info(f"  Execution Time: {result.execution_time_ms}ms")
        logger.info("=" * 60)

        return result

    def _load_missing_skus(self) -> list:
        """Load missing SKUs from catalog_coverage.csv."""
        if not COVERAGE_CSV.exists():
            logger.warning(f"Coverage CSV not found: {COVERAGE_CSV}")
            return []

        skus = []
        try:
            with open(COVERAGE_CSV, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("torob_match", "").strip().lower() == "no":
                        sku = row.get("extracted_sku", "").strip()
                        if sku:
                            skus.append(sku)
        except Exception as e:
            logger.error(f"Failed to read coverage CSV: {e}")

        return skus

    def _patch_torob_catalog(self, recovered: list) -> None:
        """Append recovered products to the Torob catalog CSV."""
        if not TOROB_CSV.exists():
            logger.error(f"Torob catalog CSV not found: {TOROB_CSV}")
            return

        # Backup first
        if not TOROB_CSV_BACKUP.exists():
            shutil.copy2(TOROB_CSV, TOROB_CSV_BACKUP)
            logger.info(f"Backup created: {TOROB_CSV_BACKUP}")

        # Read existing product IDs
        existing_ids = set()
        with open(TOROB_CSV, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("product_id", "")
                if pid:
                    existing_ids.add(pid)

        # Append new products
        new_count = 0
        with open(TOROB_CSV, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["product_url", "product_id", "title", "category", "brand"])
            for product in recovered:
                pid = product.product_id
                if pid and pid not in existing_ids:
                    writer.writerow({
                        "product_url": product.url,
                        "product_id": pid,
                        "title": product.title,
                        "category": product.category or "recovered",
                        "brand": "بوش",
                    })
                    existing_ids.add(pid)
                    new_count += 1

        logger.info(f"Patched {new_count} products into Torob catalog")

    def _rebuild_matcher(self) -> None:
        """Rebuild matcher indexes and Watch List."""
        project_root = Path(__file__).resolve().parent.parent
        matcher_script = project_root / "matcher" / "main.py"

        logger.info("Rebuilding matcher indexes and Watch List...")
        result = subprocess.run(
            [sys.executable, str(matcher_script)],
            capture_output=True, text=True,
            cwd=str(project_root),
            timeout=300,
        )

        if result.returncode == 0:
            logger.info("Matcher rebuild completed successfully")
            if result.stdout:
                logger.debug(f"Matcher output: {result.stdout[-500:]}")
        else:
            logger.error(f"Matcher rebuild failed (exit code {result.returncode})")
            if result.stderr:
                logger.error(f"Matcher stderr: {result.stderr[-500:]}")
            raise RuntimeError(f"Matcher rebuild failed: exit code {result.returncode}")
