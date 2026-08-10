"""System health endpoint."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.base import get_session
from db.models import MonitorRun

logger = logging.getLogger("api.routers.health")

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)):
    """System health check."""
    db_ok = False
    try:
        await session.execute(select(1))
        db_ok = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    last_run = await session.execute(
        select(MonitorRun).order_by(MonitorRun.id.desc()).limit(1)
    )
    last_run_row = last_run.scalar_one_or_none()
    last_run_info = {}
    if last_run_row:
        last_run_info = {
            "last_run_finished_at": str(last_run_row.finished_at) if last_run_row.finished_at else None,
            "last_run_status": last_run_row.status,
            "seconds_since_last_run": int(
                (datetime.now(timezone.utc) - last_run_row.finished_at).total_seconds()
            ) if last_run_row.finished_at else None,
        }

    status = "healthy" if db_ok else "unhealthy"

    return {
        "status": status,
        "database": {"connected": db_ok},
        "monitor": last_run_info,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
