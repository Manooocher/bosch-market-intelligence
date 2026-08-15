"""Margins endpoint for profit analysis."""

import logging
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.base import get_session
from db.models import LatestPrice, WatchListProduct

logger = logging.getLogger("api.routers.margins")
router = APIRouter(prefix="/api/margins", tags=["margins"])


def _parse_toman(raw: str | None) -> int:
    """Parse a nabkade price string (may contain commas / Persian commas) to Toman."""
    if not raw:
        return 0
    try:
        return int(raw.replace(",", "").replace("،", "").strip())
    except (ValueError, AttributeError):
        return 0


def _compute_margin(lp: LatestPrice, nabkade_toman: int) -> dict:
    """Compute margin fields for a single product (in Toman)."""
    min_market = lp.min_price_rial or 0
    median_market = lp.median_price_rial or 0
    min_toman = min_market // 10 if min_market else 0
    median_toman = median_market // 10 if median_market else 0

    margin_min = nabkade_toman - min_toman if nabkade_toman > 0 and min_toman > 0 else 0
    margin_median = nabkade_toman - median_toman if nabkade_toman > 0 and median_toman > 0 else 0
    pct_min = float(Decimal(str(margin_min)) / Decimal(str(nabkade_toman)) * 100) if nabkade_toman > 0 else 0.0
    pct_median = float(Decimal(str(margin_median)) / Decimal(str(nabkade_toman)) * 100) if nabkade_toman > 0 else 0.0

    return {
        "sku": lp.sku,
        "torob_product_id": lp.torob_product_id,
        "title": lp.title,
        "category": lp.category,
        "torob_url": f"https://torob.com/p/{lp.torob_product_id}",
        "nabkade_price_toman": nabkade_toman,
        "market_min_price_toman": min_toman,
        "market_median_price_toman": median_toman,
        "margin_vs_min_toman": margin_min,
        "margin_vs_median_toman": margin_median,
        "margin_vs_min_pct": round(pct_min, 1),
        "margin_vs_median_pct": round(pct_median, 1),
        "is_profitable": margin_min > 0,
    }


@router.get("")
async def list_margins(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("margin_vs_min_pct"),
    sort_dir: str = Query("desc"),
    session: AsyncSession = Depends(get_session),
):
    """Paginated list of products sorted by margin analysis.

    Margins are computed in Python (they derive from nabkade price vs market
    prices), so all rows are fetched, computed, sorted, then sliced. Sorting is
    applied over the fully-computed margin values, not raw DB columns.
    """
    query = (
        select(WatchListProduct, LatestPrice)
        .join(LatestPrice, WatchListProduct.nabkade_product_id == LatestPrice.nabkade_product_id)
    )

    result = await session.execute(query)
    rows = result.all()

    margins = []
    for row in rows:
        wl = row[0]
        lp = row[1]
        nabkade_toman = _parse_toman(wl.nabkade_price)
        m = _compute_margin(lp, nabkade_toman)
        # Prefer the watchlist human title when present
        if wl.nabkade_title:
            m["title"] = wl.nabkade_title
        margins.append(m)

    # Sort by the requested computed margin field (fallback safely)
    sort_key = sort_by if sort_by in {
        "margin_vs_min_pct", "margin_vs_median_pct", "margin_vs_min_toman",
        "margin_vs_median_toman", "nabkade_price_toman", "market_min_price_toman",
    } else "margin_vs_min_pct"
    margins.sort(key=lambda m: m.get(sort_key, 0), reverse=(sort_dir.lower() != "asc"))

    total = len(margins)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    page_items = margins[start:start + per_page]

    return {
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
        "margins": page_items,
    }