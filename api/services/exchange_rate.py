"""Real-time exchange rate fetcher with intelligent caching.

Fetches the USD/IRR (Rial-per-USD) rate from the Tabdeal API on demand and
caches it in-memory for 1 hour. Falls back to the latest completed
``monitor_runs`` row, then to a hard-coded estimate, so the endpoint never
returns 0/None.

Source values returned in the ``source`` field:
    - ``tabdeal-live``  : fresh rate fetched from Tabdeal this request
    - ``tabdeal-cached``: fresh rate served from the in-memory cache
    - ``monitor``        : used the latest completed monitor run (Tabdeal down)
    - ``fallback``       : hard-coded estimate (all sources failed)
"""

import asyncio
import httpx
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models import MonitorRun

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_SECONDS = 3600  # 1 hour
FALLBACK_RATE_RIAL = 187790  # Rial per USD
TABDEAL_URL = "https://api1.tabdeal.org/r/api/v1/depth?symbol=USDTIRT&limit=1"

# In-memory cache
_rate_cache: dict = {
    "value": None,
    "timestamp": None,
    "source": None,
}


async def fetch_from_tabdeal(timeout: float = 10.0) -> Optional[int]:
    """
    Fetch the current USD/IRR rate from the Tabdeal API.

    Returns:
        Exchange rate in Rial per USD, or None if the fetch fails.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(TABDEAL_URL)
            response.raise_for_status()

            data = response.json()
            asks = data.get("asks", [])

            if not asks or not asks[0]:
                logger.warning("Tabdeal API returned no asks")
                return None

            # asks[0][0] is the best ask price (string like "185703.000...")
            rate_str = str(asks[0][0])
            rate = int(float(rate_str))

            if rate <= 0:
                logger.warning(f"Tabdeal returned invalid rate: {rate}")
                return None

            logger.info(f"Fetched live rate from Tabdeal: {rate} Rial/USD")
            return rate

    except (httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError, TypeError) as e:
        logger.warning(f"Failed to fetch from Tabdeal: {e}")
        return None


async def get_latest_monitor_run_rate(session: AsyncSession) -> Optional[int]:
    """
    Get the exchange rate from the latest successful monitor run.

    Used as a fallback when the live fetch fails.
    """
    try:
        stmt = (
            select(MonitorRun.exchange_rate_rial)
            .where(MonitorRun.status == "completed")
            .where(MonitorRun.exchange_rate_rial.isnot(None))
            .where(MonitorRun.exchange_rate_rial > 0)
            .order_by(MonitorRun.id.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        rate = result.scalar()

        if rate and rate > 0:
            logger.info(f"Using monitor_runs rate: {rate} Rial/USD")
            return rate
        return None
    except Exception as e:  # noqa: BLE001 - defensive fallback boundary
        logger.error(f"Failed to read monitor_runs: {e}")
        return None


async def get_fresh_exchange_rate(session: AsyncSession) -> dict:
    """
    Get a fresh exchange rate with smart caching.

    Strategy:
        1. Check the in-memory cache (TTL: 1 hour).
        2. If stale/empty, fetch from the Tabdeal API.
        3. If Tabdeal fails, fall back to ``monitor_runs``.
        4. As a last resort use the hard-coded estimate.
        5. Never return 0 or None.

    Returns:
        {
            "value": int,      # Rial per USD
            "source": str,     # tabdeal-live | tabdeal-cached | monitor | fallback
            "timestamp": str,  # ISO timestamp
        }
    """
    now = datetime.now(timezone.utc)

    # Step 1: Serve from an in-memory cache when it is still fresh.
    if _rate_cache["value"] and _rate_cache["timestamp"]:
        age_seconds = (now - _rate_cache["timestamp"]).total_seconds()
        if age_seconds < CACHE_TTL_SECONDS:
            logger.debug(
                f"Using cached rate: {_rate_cache['value']} (age: {age_seconds:.0f}s)"
            )
            return {
                "value": _rate_cache["value"],
                "source": "tabdeal-cached",
                "timestamp": _rate_cache["timestamp"].isoformat(),
            }

    # Step 2: Fetch a live rate from Tabdeal.
    rate = await fetch_from_tabdeal()
    if rate:
        _rate_cache["value"] = rate
        _rate_cache["timestamp"] = now
        _rate_cache["source"] = "tabdeal-live"
        return {"value": rate, "source": "tabdeal-live", "timestamp": now.isoformat()}

    # Step 3: Fall back to the latest completed monitor run.
    rate = await get_latest_monitor_run_rate(session)
    if rate:
        _rate_cache["value"] = rate
        _rate_cache["timestamp"] = now
        _rate_cache["source"] = "monitor"
        return {"value": rate, "source": "monitor", "timestamp": now.isoformat()}

    # Step 4: Hard fallback (should never be reached under normal operation).
    logger.warning("All rate sources failed, using hard fallback")
    _rate_cache["value"] = FALLBACK_RATE_RIAL
    _rate_cache["timestamp"] = now
    _rate_cache["source"] = "fallback"
    return {
        "value": FALLBACK_RATE_RIAL,
        "source": "fallback",
        "timestamp": now.isoformat(),
    }