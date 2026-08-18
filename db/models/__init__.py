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
    original_price_rial = Column(BigInteger, default=0)
    has_discount = Column(Boolean, default=False)
    shipping_cost = Column(BigInteger, default=0)
    offer_url = Column(Text)
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
    category = Column(String(255))
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
    all_torob_ids = Column(Text, default="[]")
    match_count = Column(Integer, default=0)
    confidence_score = Column(Numeric(10, 4), default=0.0)
    confidence_level = Column(String(20), default="none")
    match_method = Column(String(50), default="none")
    status = Column(String(20), default="no_match")
    review_state = Column(String(30), default="auto_accepted")
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))


class ProductStatus(Base):
    __tablename__ = "product_status"

    torob_product_id = Column(String(255), primary_key=True)
    status = Column(String(20), nullable=False, default="unknown")
    detected_at = Column(DateTime(timezone=True))
    last_successful_fetch = Column(DateTime(timezone=True))
    error_detail = Column(Text)


class MonitorLog(Base):
    """Event log for monitor runs (previously SQLite monitor_log)."""
    __tablename__ = "monitor_log"
    __table_args__ = (Index("idx_monitor_log_run", "monitor_run_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_run_id = Column(Integer, nullable=False)
    nabkade_product_id = Column(String(255))
    event = Column(String(50))
    detail = Column(Text)
    timestamp = Column(DateTime(timezone=True), nullable=False)


class ProxySession(Base):
    """Proxy session health tracking (previously SQLite proxy_sessions)."""
    __tablename__ = "proxy_sessions"

    session_id = Column(String(100), primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    last_used = Column(DateTime(timezone=True))
    request_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_490_count = Column(Integer, default=0)
    error_429_count = Column(Integer, default=0)
    error_5xx_count = Column(Integer, default=0)
    timeout_count = Column(Integer, default=0)
    total_latency_ms = Column(BigInteger, default=0)
    is_quarantined = Column(Boolean, default=False)
    quarantine_reason = Column(Text, default="")
    quarantine_until = Column(DateTime(timezone=True))


class MatchCandidate(Base):
    """Scored match candidates (previously SQLite match_candidates)."""
    __tablename__ = "match_candidates"
    __table_args__ = (
        Index("idx_candidates_nabkade", "nabkade_product_id"),
        Index("idx_candidates_torob", "torob_product_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    nabkade_product_id = Column(String(255), nullable=False)
    torob_product_id = Column(String(255), nullable=False)
    score = Column(Numeric(10, 4), default=0.0)
    signals = Column(Text)
    match_source = Column(String(50))
    rank = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True))


class ReviewQueue(Base):
    """Products requiring manual review (previously SQLite review_queue)."""
    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nabkade_product_id = Column(String(255))
    nabkade_title = Column(Text)
    nabkade_url = Column(Text)
    nabkade_price = Column(String(50))
    candidate_list = Column(Text)
    confidence_score = Column(Numeric(10, 4), default=0.0)
    confidence_level = Column(String(20), default="low")
    review_reason = Column(Text)
    status = Column(String(20), default="pending")
    reviewer = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True))
    reviewed_at = Column(DateTime(timezone=True))


class MatchingLog(Base):
    """Audit trail of matcher decisions (previously SQLite matching_logs)."""
    __tablename__ = "matching_logs"
    __table_args__ = (Index("idx_logs_nabkade", "nabkade_product_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    nabkade_product_id = Column(String(255))
    action = Column(String(50))
    details = Column(Text)
    timestamp = Column(DateTime(timezone=True))


# ── Shipments (Phase 7) ─────────────────────────────────────────────────────
class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    dollar_rate = Column(Numeric)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finalized_at = Column(DateTime(timezone=True))

    items = relationship("ShipmentItem", back_populates="shipment", cascade="all, delete-orphan")
    costs = relationship("ShipmentCost", back_populates="shipment", cascade="all, delete-orphan")


class ShipmentItem(Base):
    __tablename__ = "shipment_items"
    __table_args__ = (Index("idx_shipment_items_shipment", "shipment_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    nabkade_product_id = Column(String(255))
    torob_product_id = Column(String(255))
    sku = Column(String(50))
    title = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_purchase_price_usd = Column(Numeric, nullable=False, default=0)
    allocated_cost_usd = Column(Numeric, default=0)
    landed_cost_usd = Column(Numeric, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shipment = relationship("Shipment", back_populates="items")


class ShipmentCost(Base):
    __tablename__ = "shipment_costs"
    __table_args__ = (Index("idx_shipment_costs_shipment", "shipment_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    cost_type = Column(String(50), nullable=False)  # shipping|customs|insurance|warehouse|handling|other
    description = Column(Text)
    amount_usd = Column(Numeric, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shipment = relationship("Shipment", back_populates="costs")
