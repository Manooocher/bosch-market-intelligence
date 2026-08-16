"""Products endpoints — list and detail."""

import logging
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, or_
from db.base import get_session
from db.models import LatestPrice, SellerSnapshot, MarketSnapshot, WatchListProduct

logger = logging.getLogger("api.routers.products")
router = APIRouter(prefix="/api/products", tags=["products"])


def _build_product_response(product: LatestPrice, nabkade_price_str: str | None = None) -> dict:
    """Build a single product dict with category, torob_url, and margin fields."""
    torob_url = f"https://torob.com/p/{product.torob_product_id}"

    # Compute margin from nabkade price (in Toman) vs market prices (in Rial)
    nabkade_toman = 0
    if nabkade_price_str:
        try:
            nabkade_toman = int(nabkade_price_str.replace(",", "").replace("،", "").strip())
        except (ValueError, AttributeError):
            nabkade_toman = 0

    # Market prices are already stored in Toman (despite the _rial column name)
    min_rial = product.min_price_rial or 0
    median_rial = product.median_price_rial or 0
    min_toman = min_rial if min_rial else 0
    median_toman = median_rial if median_rial else 0

    margin_vs_min_rial = nabkade_toman - min_toman if nabkade_toman > 0 and min_toman > 0 else 0
    margin_vs_median_rial = nabkade_toman - median_toman if nabkade_toman > 0 and median_toman > 0 else 0
    margin_vs_min_pct = float(Decimal(str(margin_vs_min_rial)) / Decimal(str(nabkade_toman)) * 100) if nabkade_toman > 0 else 0.0
    margin_vs_median_pct = float(Decimal(str(margin_vs_median_rial)) / Decimal(str(nabkade_toman)) * 100) if nabkade_toman > 0 else 0.0

    return {
        "nabkade_product_id": product.nabkade_product_id,
        "torob_product_id": product.torob_product_id,
        "sku": product.sku,
        "title": product.title,
        "category": product.category,
        "torob_url": torob_url,
        "last_fetched_at": str(product.last_fetched_at) if product.last_fetched_at else None,
        "seller_count": product.seller_count or 0,
        "min_price_rial": product.min_price_rial or 0,
        "max_price_rial": product.max_price_rial or 0,
        "avg_price_rial": product.avg_price_rial or 0,
        "median_price_rial": product.median_price_rial or 0,
        "min_price_usd": product.min_price_usd or 0,
        "max_price_usd": product.max_price_usd or 0,
        "avg_price_usd": product.avg_price_usd or 0,
        "median_price_usd": product.median_price_usd or 0,
        "competition_score": product.competition_score or 0,
        "margin_vs_min_pct": round(margin_vs_min_pct, 1),
        "margin_vs_min_rial": margin_vs_min_rial,
        "margin_vs_median_pct": round(margin_vs_median_pct, 1),
        "margin_vs_median_rial": margin_vs_median_rial,
        "updated_at": str(product.updated_at) if product.updated_at else None,
    }


@router.get("")
async def list_products(
    page: int = Query(1, ge=1),
    per_page: int | None = Query(None, ge=1, le=1000),
    sort_by: str = Query("competition_score"),
    sort_dir: str = Query("desc"),
    search: str | None = Query(None),
    category: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """List products.

    By default returns ALL products matching filters in one response
    (the dashboard virtualizes client-side). Pagination is only applied when
    the client explicitly passes `per_page`.
    """
    # Build filter conditions (applied to both count and data queries)
    filters = []
    if search:
        filters.append(
            or_(
                LatestPrice.title.ilike(f"%{search}%"),
                LatestPrice.sku.ilike(f"%{search}%"),
            )
        )
    if category:
        filters.append(LatestPrice.category == category)

    # Count total (respects filters)
    count_query = select(func.count(LatestPrice.nabkade_product_id))
    if filters:
        count_query = count_query.where(*filters)
    total = await session.scalar(count_query) or 0

    # Build query with join to watch_list for nabkade_price (margin computation)
    query = (
        select(LatestPrice, WatchListProduct.nabkade_price)
        .outerjoin(WatchListProduct, LatestPrice.nabkade_product_id == WatchListProduct.nabkade_product_id)
    )
    if filters:
        query = query.where(*filters)

    # Apply sorting
    sort_col = getattr(LatestPrice, sort_by, LatestPrice.competition_score)
    if sort_dir == "asc":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    # Pagination only if explicitly requested
    pagination_disabled = per_page is None
    if not pagination_disabled:
        query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    rows = result.all()

    products = []
    for row in rows:
        lp = row[0]  # LatestPrice
        nabkade_price = row[1]  # WatchListProduct.nabkade_price or None
        products.append(_build_product_response(lp, nabkade_price))

    if pagination_disabled:
        return {
            "pagination": {
                "page": 1,
                "per_page": total or 1,
                "total": total,
                "total_pages": 1,
            },
            "pagination_disabled": True,
            "products": products,
        }

    total_pages = max(1, (total + per_page - 1) // per_page)
    return {
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
        "pagination_disabled": False,
        "products": products,
    }


@router.get("/{torob_id}")
async def get_product(
    torob_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Detailed product view with price distribution."""
    result = await session.execute(
        select(LatestPrice, WatchListProduct.nabkade_price)
        .outerjoin(WatchListProduct, LatestPrice.nabkade_product_id == WatchListProduct.nabkade_product_id)
        .where(LatestPrice.torob_product_id == torob_id)
    )
    row = result.one_or_none()

    if not row:
        return {"error": "Product not found", "torob_product_id": torob_id}

    product = row[0]
    nabkade_price = row[1]

    # Get sellers for this specific product (via its market snapshots)
    sellers_q = await session.execute(
        select(SellerSnapshot)
        .join(MarketSnapshot, SellerSnapshot.market_snapshot_id == MarketSnapshot.id)
        .where(MarketSnapshot.torob_product_id == torob_id)
    )
    sellers = sellers_q.scalars().all()

    # Price distribution
    min_p = product.min_price_rial or 0
    max_p = product.max_price_rial or 0
    spread = max_p - min_p if max_p > min_p else 0
    bucket = max(1, spread // 4)
    distribution = []
    for i in range(4):
        lo = min_p + i * bucket
        hi = min_p + (i + 1) * bucket if i < 3 else max_p
        count = sum(1 for s in sellers if lo <= (s.price_rial or 0) < hi) if i < 3 \
            else sum(1 for s in sellers if lo <= (s.price_rial or 0) <= hi)
        distribution.append({"range": f"{lo//1000000}M-{hi//1000000}M", "count": count})

    freshness = "unknown"
    if product.last_fetched_at:
        age = datetime.now(timezone.utc) - product.last_fetched_at
        if age < timedelta(hours=24):
            freshness = "fresh"
        elif age < timedelta(hours=96):
            freshness = "acceptable"
        else:
            freshness = "stale"

    base = _build_product_response(product, nabkade_price)

    return {
        **base,
        "market_stats": {
            "seller_count": product.seller_count or 0,
            "min_price_rial": product.min_price_rial or 0,
            "max_price_rial": product.max_price_rial or 0,
            "avg_price_rial": product.avg_price_rial or 0,
            "median_price_rial": product.median_price_rial or 0,
            "competition_score": product.competition_score or 0,
            "fetched_at": str(product.last_fetched_at) if product.last_fetched_at else None,
            "freshness": freshness,
        },
        "price_distribution": {"buckets": distribution},
    }


@router.get("/{torob_id}/sellers")
async def get_sellers(
    torob_id: str,
    session: AsyncSession = Depends(get_session),
):
    """List of sellers for a product, sorted by price."""
    result = await session.execute(
        select(SellerSnapshot)
        .join(MarketSnapshot, SellerSnapshot.market_snapshot_id == MarketSnapshot.id)
        .where(MarketSnapshot.torob_product_id == torob_id)
        .order_by(SellerSnapshot.price_rial)
    )
    sellers = [
        {
            "seller_id": s.seller_id,
            "seller_name": s.seller_name,
            "price_rial": s.price_rial,
            "seller_score": s.seller_score,
            "seller_city": s.seller_city,
            "is_in_stock": s.is_in_stock,
            "is_promoted": s.is_promoted,
        }
        for s in result.scalars().all()
    ]
    return {"torob_product_id": torob_id, "sellers": sellers}
