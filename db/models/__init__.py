"""SQLAlchemy ORM models for PostgreSQL."""

from db.base import Base
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Numeric, Boolean,
    DateTime, ForeignKey, Index, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB


class MarketSnapshot(Base):
    __tablename__ = "market_snapshot"
    __table_args__ = (
        Index("idx_snapshot_product_time", "torob_product_id", "fetched_at"),
        Index("idx_snapshot_run", "monitor_run_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_run_id = Column(Integer, nullable=False)
    nabkade_product_id = Column(String(255), nullable=False)
    torob_product_id = Column(String(255), nullable=False, index=True)
    sku = Column(String(50))
    title = Column(Text)
    category = Column(String(255))

    seller_count = Column(Integer, default=0)
    min_price_rial = Column(BigInteger, default=0)
    max_price_rial = Column(BigInteger, default=0)
    avg_price_rial = Column(BigInteger, default=0)
    median_price_rial = Column(BigInteger, default=0)
    min_price_usd = Column(BigInteger, default=0)
    max_price_usd = Column(BigInteger, default=0)
    avg_price_usd = Column(BigInteger, default=0)
    median_price_usd = Column(BigInteger, default=0)

    competition_score = Column(Integer, default=0)
    price_compression = Column(Numeric(10, 4), default=0)
    price_dispersion = Column(Numeric(10, 4), default=0)
    price_spread = Column(BigInteger, default=0)

    source_method = Column(String(50), default="sellers_api")
    total_sellers_raw = Column(Integer, default=0)
    in_stock_count = Column(Integer, default=0)

    fetched_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    sellers = relationship("SellerSnapshot", back_populates="market_snapshot")


class SellerSnapshot(Base):
    __tablename__ = "seller_snapshot"
    __table_args__ = (
        Index("idx_seller_snapshot_id", "market_snapshot_id"),
        Index("idx_seller_price", "market_snapshot_id", "price_rial"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_snapshot_id = Column(Integer, ForeignKey("market_snapshot.id"), nullable=False)
    seller_id = Column(String(100), nullable=False)
    seller_name = Column(String(500))
    price_rial = Column(BigInteger, default=0)
    seller_score = Column(Integer, default=0)
    seller_city = Column(String(200))
    warranty_info = Column(Text)
    is_promoted = Column(Boolean, default=False)
    is_in_stock = Column(Boolean, default=True)
    extra_info_json = Column(JSONB(none_as_null=True))

    market_snapshot = relationship("MarketSnapshot", back_populates="sellers")


class MonitorRun(Base):
    __tablename__ = "monitor_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
    products_total = Column(Integer, default=0)
    products_succeeded = Column(Integer, default=0)
    products_failed = Column(Integer, default=0)
    exchange_rate_rial = Column(BigInteger, default=0)
    exchange_rate_source = Column(String(50), default="")
    duration_ms = Column(Integer, default=0)
    status = Column(String(20), default="running")


class LatestPrice(Base):
    __tablename__ = "latest_prices"
    __table_args__ = (Index("idx_latest_nabkade", "nabkade_product_id"),)

    nabkade_product_id = Column(String(255), primary_key=True)
    torob_product_id = Column(String(255), nullable=False)
    sku = Column(String(50))
    title = Column(Text)
    last_fetched_at = Column(DateTime(timezone=True))
    seller_count = Column(Integer, default=0)
    min_price_rial = Column(BigInteger, default=0)
    max_price_rial = Column(BigInteger, default=0)
    avg_price_rial = Column(BigInteger, default=0)
    median_price_rial = Column(BigInteger, default=0)
    min_price_usd = Column(BigInteger, default=0)
    max_price_usd = Column(BigInteger, default=0)
    avg_price_usd = Column(BigInteger, default=0)
    median_price_usd = Column(BigInteger, default=0)
    competition_score = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True))


class WatchListProduct(Base):
    __tablename__ = "watch_list"
    __table_args__ = (
        Index("idx_watchlist_category", "normalized_category"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    nabkade_product_id = Column(String(255), nullable=False, unique=True)
    nabkade_url = Column(Text)
    nabkade_title = Column(Text)
    nabkade_category = Column(String(255))
    nabkade_brand = Column(String(255))
    nabkade_price = Column(String(50))
    canonical_sku = Column(String(50))
    normalized_category = Column(String(255))
    preferred_torob_id = Column(String(255))
    preferred_torob_url = Column(Text)
    preferred_torob_title = Column(Text)
    confidence_level = Column(String(20), default="none")
    match_method = Column(String(50), default="none")
    status = Column(String(20), default="no_match")
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))


class ProductStatus(Base):
    __tablename__ = "product_status"

    torob_product_id = Column(String(255), primary_key=True)
    status = Column(String(20), nullable=False, default="unknown")
    detected_at = Column(DateTime(timezone=True))
    last_successful_fetch = Column(DateTime(timezone=True))
    error_detail = Column(Text)
