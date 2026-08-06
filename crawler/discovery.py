"""Category Discovery module.

Discovers product categories and crawls full category pages.
Uses TorobCrawler for all HTTP operations.
"""

import logging
from dataclasses import dataclass
from typing import Callable

from crawler.interfaces import IDiscoveryConsumer, ProductData, CrawlerResponse
from crawler.torob import TorobCrawler
from crawler.config import CrawlerMode, BOSCH_BRAND_ID

logger = logging.getLogger(__name__)


class CategoryDiscovery(IDiscoveryConsumer):
    """Discovers product categories and crawls category pages.

    Uses TorobCrawler for all HTTP operations.
    """

    def __init__(self, crawler: TorobCrawler):
        self.crawler = crawler

    def discover_categories(self, root_category_id: int = 169) -> list[dict]:
        """Discover all product categories under a root category."""
        response = self.crawler.search_bosch(page=0)
        if not response.success:
            return []

        categories = response.data.get("categories", [])
        discovered = []
        for cat in categories:
            cat_id = int(cat.get("cat_id", 0))
            title = cat.get("title", "")
            if cat_id and title:
                discovered.append({
                    "cat_id": cat_id,
                    "title": title,
                    "slug": cat.get("cat_slug", ""),
                })

        logger.info(f"Discovered {len(discovered)} categories")
        return discovered

    def crawl_category(self, category_id: int, query: str = None) -> list[ProductData]:
        """Crawl all products in a category."""
        products = []
        page = 0

        while True:
            response = self.crawler.search(
                query=query,
                page=page,
                category=category_id,
                brand=BOSCH_BRAND_ID,
            )

            if not response.success:
                break

            results = response.data.get("results", [])
            if not results:
                break

            for item in results:
                product = ProductData(
                    product_id=item.get("random_key", ""),
                    title=item.get("name1", ""),
                    url=item.get("web_client_absolute_url", ""),
                    category=str(category_id),
                    brand="بوش",
                    source=CrawlerMode.DISCOVERY,
                )
                products.append(product)

            next_url = response.data.get("next")
            if not next_url:
                break

            page += 1

        logger.info(f"Crawled category {category_id}: {len(products)} products")
        return products
