"""Market overview endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.base import get_session
from db.models import MarketSnapshot, LatestPrice, MonitorRun

router = APIRouter(prefix="/api/market", tags=["market"])

# Reasonable Rial-per-USD fallback when no historical monitor run exists.
FALLBACK_RIAL_PER_USD = 187790


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

    # Exchange rate: newest COMPLETED run with a positive recorded Rial/USD
    # rate (mirrors api/routers/shipments.py get_exchange_rate). Never return
    # 0 or None — fall back to a sensible estimate when no data exists.
    rate_stmt = (
        select(MonitorRun.exchange_rate_rial, MonitorRun.finished_at)
        .where(MonitorRun.status == "completed")
        .where(MonitorRun.exchange_rate_rial.isnot(None))
        .where(MonitorRun.exchange_rate_rial > 0)
        .order_by(MonitorRun.id.desc())
        .limit(1)
    )
    rate_row = (await session.execute(rate_stmt)).first()

    if rate_row and rate_row[0]:
        usd_rate = int(rate_row[0])
        rate_source = "tabdeal"
        rate_updated_at = str(rate_row[1]) if rate_row[1] else None
    else:
        usd_rate = FALLBACK_RIAL_PER_USD
        rate_source = "fallback"
        rate_updated_at = None

    return {
        "total_products": total,
        "products_with_sellers": products_with_sellers or 0,
        "avg_sellers_per_product": round(float(avg_sellers), 1),
        "avg_competition_score": round(float(avg_competition), 1),
        "usd_irt_rate": usd_rate,
        "usd_irt_source": rate_source,
        "usd_irt_updated_at": rate_updated_at,
        "last_monitor_run": run_info,
    }
