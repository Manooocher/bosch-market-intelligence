"""Market overview endpoint."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.base import get_session
from db.models import MarketSnapshot, LatestPrice, MonitorRun

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/overview")
async def market_overview(session: AsyncSession = Depends(get_session)):
    """Global market statistics."""
    # Total products with latest prices
    total = await session.scalar(select(func.count(LatestPrice.nabkade_product_id)))
    products_with_sellers = await session.scalar(
        select(func.count(LatestPrice.nabkade_product_id)).where(LatestPrice.seller_count > 0)
    )
    avg_sellers = await session.scalar(
        select(func.avg(LatestPrice.seller_count)).where(LatestPrice.seller_count > 0)
    ) or 0
    avg_competition = await session.scalar(
        select(func.avg(LatestPrice.competition_score))
    ) or 0

    # Last monitor run
    last_run = await session.execute(
        select(MonitorRun).order_by(MonitorRun.id.desc()).limit(1)
    )
    last_run_row = last_run.scalar_one_or_none()
    run_info = None
    if last_run_row:
        run_info = {
            "started_at": str(last_run_row.started_at),
            "finished_at": str(last_run_row.finished_at) if last_run_row.finished_at else None,
            "products_succeeded": last_run_row.products_succeeded,
            "products_failed": last_run_row.products_failed,
            "status": last_run_row.status,
        }

    return {
        "total_products": total,
        "products_with_sellers": products_with_sellers or 0,
        "avg_sellers_per_product": round(float(avg_sellers), 1),
        "avg_competition_score": round(float(avg_competition), 1),
        "usd_irt_rate": 0,
        "usd_irt_source": "tabdeal",
        "usd_irt_updated_at": datetime.now(timezone.utc).isoformat(),
        "last_monitor_run": run_info,
    }
