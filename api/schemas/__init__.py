"""Pydantic V2 schemas for API request/response validation."""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional, Literal


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
    sort_by: str = "competition_score"
    sort_dir: Literal["asc", "desc"] = "desc"


class ProductListItem(BaseModel):
    torob_product_id: str
    sku: Optional[str] = None
    title: str
    category: Optional[str] = None
    seller_count: int = 0
    in_stock_count: int = 0
    min_price_rial: int = 0
    max_price_rial: int = 0
    median_price_rial: int = 0
    competition_score: int = 0
    min_price_usd: int = 0
    freshness: str = "unknown"
    margin_vs_min_pct: Optional[float] = None
    margin_vs_median_pct: Optional[float] = None


class PriceBucket(BaseModel):
    range_label: str
    count: int


class MarginResult(BaseModel):
    nabkade_price_toman: int = 0
    nabkade_price_usd_cents: int = 0
    market_min_price_toman: int = 0
    market_median_price_toman: int = 0
    margin_vs_min_toman: int = 0
    margin_vs_median_toman: int = 0
    margin_vs_min_pct: float = 0.0
    margin_vs_median_pct: float = 0.0


class ProductDetail(BaseModel):
    torob_product_id: str
    sku: Optional[str] = None
    title: str
    category: Optional[str] = None
    nabkade_info: Optional[dict] = None
    market_stats: dict
    price_distribution: Optional[dict] = None
    margins: Optional[MarginResult] = None


class SellerInfo(BaseModel):
    seller_id: str
    seller_name: str
    price_rial: int
    seller_score: int = 0
    seller_city: Optional[str] = None
    warranty_info: Optional[str] = None
    is_promoted: bool = False
    is_in_stock: bool = True


class MarketOverview(BaseModel):
    total_products: int
    products_with_sellers: int
    avg_sellers_per_product: float
    avg_competition_score: float
    usd_irt_rate: int
    usd_irt_source: str
    usd_irt_updated_at: str
    last_monitor_run: Optional[dict] = None


class SystemHealth(BaseModel):
    status: str = "healthy"
    database: dict
    monitor: dict
    exchange_rate: dict


class PaginatedResponse(BaseModel):
    pagination: dict
    products: list = []
    margins: list = []
