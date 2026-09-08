"""Tests for the real-time exchange-rate service (api/services/exchange_rate.py).

Deterministic: Tabdeal and the database are mocked — no network, no DB, no
wall-clock dependency beyond the cache TTL.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from api.services import exchange_rate as er


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the module-level in-memory cache between tests."""
    er._rate_cache = {"value": None, "timestamp": None, "source": None}
    yield
    er._rate_cache = {"value": None, "timestamp": None, "source": None}


@pytest.mark.asyncio
async def test_live_fetch_success():
    with patch.object(er, "fetch_from_tabdeal", AsyncMock(return_value=185000)) as mock:
        info = await er.get_fresh_exchange_rate(AsyncMock())
    mock.assert_awaited_once()
    assert info["value"] == 185000
    assert info["source"] == "tabdeal-live"
    assert info["timestamp"]


@pytest.mark.asyncio
async def test_cached_served_within_ttl():
    er._rate_cache = {
        "value": 185000,
        "timestamp": datetime.now(timezone.utc) - timedelta(seconds=60),
        "source": "tabdeal-live",
    }
    with patch.object(er, "fetch_from_tabdeal", AsyncMock()) as fetch:
        info = await er.get_fresh_exchange_rate(AsyncMock())
    fetch.assert_not_awaited()  # served from cache, no network call
    assert info["value"] == 185000
    assert info["timestamp"]


@pytest.mark.asyncio
async def test_monitor_fallback_when_tabdeal_fails():
    with patch.object(er, "fetch_from_tabdeal", AsyncMock(return_value=None)), \
         patch.object(er, "get_latest_monitor_run_rate", AsyncMock(return_value=185703)):
        info = await er.get_fresh_exchange_rate(AsyncMock())
    assert info["source"] == "monitor"
    assert info["value"] == 185703


@pytest.mark.asyncio
async def test_hard_fallback_when_all_sources_fail():
    session = AsyncMock()
    with patch.object(er, "fetch_from_tabdeal", AsyncMock(return_value=None)), \
         patch.object(er, "get_latest_monitor_run_rate", AsyncMock(return_value=None)):
        info = await er.get_fresh_exchange_rate(session)
    assert info["source"] == "fallback"
    assert info["value"] == er.FALLBACK_RATE_RIAL


@pytest.mark.asyncio
async def test_fetch_from_tabdeal_parses_asks():
    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"asks": [["185703.0000000000000000", "262"]]}

    async def fake_get(*args, **kwargs):
        return FakeResp()

    with patch.object(er.httpx.AsyncClient, "get", fake_get):
        rate = await er.fetch_from_tabdeal()
    assert rate == 185703


@pytest.mark.asyncio
async def test_fetch_from_tabdeal_returns_none_on_error():
    async def boom(*args, **kwargs):
        raise er.httpx.ConnectError("boom")

    with patch.object(er.httpx.AsyncClient, "get", boom):
        rate = await er.fetch_from_tabdeal()
    assert rate is None


@pytest.mark.asyncio
async def test_fetch_from_tabdeal_invalid_zero():
    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"asks": [["0.0", "1"]]}

    async def fake_get(*args, **kwargs):
        return FakeResp()

    with patch.object(er.httpx.AsyncClient, "get", fake_get):
        rate = await er.fetch_from_tabdeal()
    assert rate is None