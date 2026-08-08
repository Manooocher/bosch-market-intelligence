"""Torob-specific crawler adapter.

Thin wrapper around HttpClient.
No retry logic, no proxy logic, no scheduler, no metrics.
Everything comes from infrastructure.
"""

import logging
from dataclasses import dataclass
from typing import Any

from crawler.config import CrawlerConfig
from crawler.http_client import HttpClient, Response

logger = logging.getLogger(__name__)


@dataclass
class CrawlerResponse:
    """Parsed Torob response."""
    success: bool
    data: Any = None
    status_code: int = 0
    error: str = ""


class TorobCrawler:
    """Adapter that wraps HttpClient for Torob-specific API calls.

    Responsibilities: build URL, prepare params, call HttpClient, parse response.
    Nothing else.
    """

    def __init__(self, client: HttpClient, config: CrawlerConfig | None = None):
        self.client = client
        self.config = config or CrawlerConfig()

    def search(self, query: str, page: int = 0, size: int = None,
               brand: int = None, category: int = None) -> CrawlerResponse:
        size = size or self.config.page_size
        params = {"page": page, "size": size}
        if query:
            params["q"] = query
        if brand is not None:
            params["brand"] = brand
        if category is not None:
            params["category"] = category

        resp = self.client.request(self.config.endpoints.search, params=params)
        return CrawlerResponse(
            success=resp.success, data=resp.data,
            status_code=resp.status_code, error=resp.error,
        )

    def get_product_details(self, product_id: str) -> CrawlerResponse:
        """Fetch product details (metadata only, no seller list)."""
        params = {"prk": product_id, "source": "torob_search"}
        resp = self.client.request(self.config.endpoints.details, params=params)
        return CrawlerResponse(
            success=resp.success, data=resp.data,
            status_code=resp.status_code, error=resp.error,
        )

    def get_sellers(self, product_id: str) -> CrawlerResponse:
        """Fetch full seller list for a product (up to 50 sellers).

        Uses the dedicated sellers endpoint:
        /base-product/sellers/?prk=<product_id>
        """
        url = f"{self.config.endpoints.api_base}/base-product/sellers/?prk={product_id}"
        resp = self.client.request(url)
        return CrawlerResponse(
            success=resp.success, data=resp.data,
            status_code=resp.status_code, error=resp.error,
        )

    def get_categories(self) -> CrawlerResponse:
        resp = self.client.request(self.config.endpoints.brand_list)
        return CrawlerResponse(
            success=resp.success, data=resp.data,
            status_code=resp.status_code, error=resp.error,
        )

    def warm_up(self) -> CrawlerResponse:
        resp = self.client.request(self.config.endpoints.homepage)
        return CrawlerResponse(
            success=resp.success, data=resp.data,
            status_code=resp.status_code, error=resp.error,
        )

    def search_bosch(self, query: str = None, page: int = 0) -> CrawlerResponse:
        q = query or self.config.bosch_queries[0]
        return self.search(q, page=page, brand=self.config.bosch_brand_id)

    def close(self):
        self.client.close()
