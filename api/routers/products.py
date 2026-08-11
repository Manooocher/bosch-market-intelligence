"""Products endpoints — list and detail."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc
from db.base import get_session
from db.models import LatestPrice, SellerSnapshot, MarketSnapshot

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("")
async def list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("competition_score"),
    sort_dir: str = Query("desc"),
    session: AsyncSession = Depends(get_session),
):
    """Paginated list of products with sorting."""
    query = select(LatestPrice)

    # Count total
    count_query = select(func.count(LatestPrice.nabkade_product_id))
    total = await session.scalar(count_query) or 0
    total_pages = max(1, (total + per_page - 1) // per_page)

    # Apply sorting
    sort_col = getattr(LatestPrice, sort_by, LatestPrice.competition_score)
    if sort_dir == "asc":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    # Apply pagination
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    cols = [c.name for c in LatestPrice.__table__.columns]
    products = [{c: getattr(row, c) for c in cols} for row in result.scalars().all()]

    return {
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
        "products": products,
    }


@router.get("/{torob_id}")
async def get_product(
    torob_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Detailed product view with price distribution."""
    result = await session.execute(
        select(LatestPrice).where(LatestPrice.torob_product_id == torob_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        return {"error": "Product not found", "torob_product_id": torob_id}

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

    return {
        "torob_product_id": torob_id,
        "sku": product.sku,
        "title": product.title,
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
