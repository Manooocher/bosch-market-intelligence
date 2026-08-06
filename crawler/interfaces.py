"""Abstract interfaces for the crawler layer.

All consumers MUST program against these interfaces.
Never depend on concrete implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CrawlerResponse:
    """Unified response from any crawler operation."""
    success: bool
    data: Any = None
    status_code: int = 0
    error: str = ""


@dataclass
class ProductData:
    """Standard product representation across the system."""
    product_id: str
    title: str
    url: str
    category: str = ""
    brand: str = ""
    price: str = ""
    image_url: str = ""
    in_stock: bool = True
    source: str = ""


class ICrawler(ABC):
    """Base interface for all HTTP operations against Torob."""

    @abstractmethod
    def search(self, query: str, page: int = 0, size: int = 48) -> CrawlerResponse:
        pass

    @abstractmethod
    def get_product_details(self, product_id: str) -> CrawlerResponse:
        pass

    @abstractmethod
    def get_categories(self) -> CrawlerResponse:
        pass

    @abstractmethod
    def warm_up(self) -> CrawlerResponse:
        pass
