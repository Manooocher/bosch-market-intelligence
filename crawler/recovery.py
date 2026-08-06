"""Catalog Recovery module.

Searches for missing SKUs using the shared crawler infrastructure.
Recovery NEVER makes direct HTTP requests — always through TorobCrawler.
"""

import logging
from dataclasses import dataclass
from typing import Callable

from crawler.interfaces import ProductData
from crawler.torob import TorobCrawler

logger = logging.getLogger(__name__)


@dataclass
class RecoveryResult:
    """Result of a single SKU recovery attempt."""
    sku: str
    found: bool
    product: ProductData | None = None
    error: str = ""


class CatalogRecovery:
    """Recovers missing products from Torob catalog.

    Uses TorobCrawler for all HTTP operations.
    Never makes direct HTTP requests.
    """

    def __init__(self, crawler: TorobCrawler):
        self.crawler = crawler
        self.results: list[RecoveryResult] = []

    def recover_missing_skus(
        self,
        sku_list: list[str],
        on_progress: Callable = None,
    ) -> list[ProductData]:
        """Search for specific SKUs that are missing from the catalog."""
        recovered = []
        total = len(sku_list)

        for i, sku in enumerate(sku_list):
            if on_progress:
                on_progress(i + 1, total, sku)

            result = self._search_sku(sku)
            self.results.append(result)

            if result.found and result.product:
                recovered.append(result.product)

        logger.info(f"Recovery complete: {len(recovered)}/{total} recovered")
        return recovered

    def _search_sku(self, sku: str) -> RecoveryResult:
        """Search for a single SKU on Torob."""
        try:
            response = self.crawler.search(sku, size=5)
            if not response.success:
                return RecoveryResult(sku=sku, found=False, error="search_failed")

            results = response.data.get("results", [])
            for item in results:
                title = item.get("name1", "")
                if sku.upper() in title.upper():
                    product = ProductData(
                        product_id=item.get("random_key", ""),
                        title=title,
                        url=item.get("web_client_absolute_url", ""),
                        brand="بوش",
                        source="recovery",
                    )
                    return RecoveryResult(sku=sku, found=True, product=product)

            return RecoveryResult(sku=sku, found=False, error="not_found")

        except Exception as e:
            logger.warning(f"Recovery failed for {sku}: {e}")
            return RecoveryResult(sku=sku, found=False, error=str(e))

    def get_statistics(self) -> dict:
        """Get recovery statistics."""
        total = len(self.results)
        found = sum(1 for r in self.results if r.found)
        not_found = sum(1 for r in self.results if not r.found and r.error == "not_found")
        errors = sum(1 for r in self.results if r.error and r.error != "not_found")

        return {
            "total": total,
            "found": found,
            "not_found": not_found,
            "errors": errors,
            "recovery_rate": found / total if total > 0 else 0,
        }
