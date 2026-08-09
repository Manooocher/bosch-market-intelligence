"""Margins endpoint for profit analysis."""

import logging
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from db.base import get_session
from db.models import LatestPrice, WatchListProduct

router = APIRouter(prefix="/api/margins", tags=["margins"])


@router.get("")
async def list_margins(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("margin_vs_min_pct"),
    sort_dir: str = Query("desc"),
    session: AsyncSession = Depends(get_session),
):
    """List products sorted by margin analysis."""
    query = (
        select(WatchListProduct, LatestPrice)
        .join(LatestPrice, WatchListProduct.nabkade_product_id == LatestPrice.nabkade_product_id)
    )

    result = await session.execute(query.offset((page - 1) * per_page).limit(per_page))
    rows = result.all()

    margins = []
    for row in rows:
        wl = row[0]
        lp = row[1]

        nabkade_toman = 0
        if wl.nabkade_price:
            try:
                nabkade_toman = int(wl.nabkade_price.replace(",", "").replace("،", "").strip())
            except ValueError:
                nabkade_toman = 0

        min_market = lp.min_price_rial or 0
        median_market = lp.median_price_rial or 0
        min_toman = min_market // 10 if min_market else 0
        median_toman = median_market // 10 if median_market else 0

        margin_min = nabkade_toman - min_toman if nabkade_toman > 0 and min_toman > 0 else 0
        margin_median = nabkade_toman - median_toman if nabkade_toman > 0 and median_toman > 0 else 0
        pct_min = float(Decimal(str(margin_min)) / Decimal(str(nabkade_toman)) * 100) if nabkade_toman > 0 else 0.0
        pct_median = float(Decimal(str(margin_median)) / Decimal(str(nabkade_toman)) * 100) if nabkade_toman > 0 else 0.0

        margins.append({
            "sku": lp.sku,
            "title": wl.nabkade_title,
            "nabkade_price_toman": nabkade_toman,
            "market_min_price_toman": min_toman,
            "margin_vs_min_toman": margin_min,
            "margin_vs_min_pct": round(pct_min, 1),
            "is_profitable": margin_min > 0,
        })

    return {"margins": margins}
