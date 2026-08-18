"""Integration tests for the Shipment module (Phase 7.4).

These hit a REAL running uvicorn server + PostgreSQL over HTTP (as the app runs
in production), rather than TestClient's in-process portal — avoiding asyncpg
connection-reuse conflicts. A session fixture starts uvicorn on a test port.

Run: python -m pytest tests/test_shipments_integration.py -v
"""
import os
import socket
import subprocess
import sys
import time

import httpx
import pytest

from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BASE_PORT = 8010


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="session")
def server_url():
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(ROOT),
        env={**os.environ, "DB_PASSWORD": "SecurePassword123"},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    # wait for readiness (trust_env=False to bypass ambient HTTP/SOCKS proxy vars)
    for _ in range(40):
        try:
            httpx.get(f"{base}/api/system/health", timeout=2, trust_env=False)
            break
        except Exception:
            time.sleep(0.5)
    yield base
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture()
def client(server_url):
    with httpx.Client(base_url=server_url, timeout=30, trust_env=False) as c:
        yield c


def _cleanup(server_url):
    # DB-level cleanup via sync layer (no event loop issues)
    from db.sync import connect
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM shipment_items WHERE shipment_id IN "
                    "(SELECT id FROM shipments WHERE name LIKE 'ZZTEST%')")
        cur.execute("DELETE FROM shipment_costs WHERE shipment_id IN "
                    "(SELECT id FROM shipments WHERE name LIKE 'ZZTEST%')")
        cur.execute("DELETE FROM shipments WHERE name LIKE 'ZZTEST%'")
        conn.commit()
    finally:
        cur.close()
        conn.close()


@pytest.fixture(autouse=True)
def cleanup(server_url):
    _cleanup(server_url)
    yield
    _cleanup(server_url)


WASHER_TOROB = "4e47d29c-f134-4ca3-8ef2-04374ab3845b"  # BGL8PRO5 (has market data)

PAYLOAD = {
    "name": "ZZTEST Integration",
    "notes": "integration",
    "items": [
        {"title": "Washer", "sku": "BGL8PRO5", "quantity": 20,
         "unit_purchase_price_usd": 450, "torob_product_id": WASHER_TOROB},
        {"title": "Vacuum", "sku": "NOPE-SKU-999", "quantity": 10,
         "unit_purchase_price_usd": 200},
    ],
    "costs": [
        {"cost_type": "shipping", "description": "sea", "amount_usd": 1500},
        {"cost_type": "customs", "description": "duty", "amount_usd": 800},
    ],
}


def test_create_shipment(client):
    r = client.post("/api/shipments", json=PAYLOAD)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "draft"
    assert d["name"] == "ZZTEST Integration"
    assert len(d["items"]) == 2
    assert len(d["costs"]) == 2


def test_calculation_verification(client):
    d = client.post("/api/shipments", json=PAYLOAD).json()
    assert float(d["total_value_usd"]) == 11000.0
    assert float(d["total_costs_usd"]) == 2300.0
    washer, vacuum = d["items"][0], d["items"][1]
    assert float(washer["landed_cost_usd"]) == pytest.approx(544.09, abs=0.02)
    assert float(washer["allocated_cost_per_unit_usd"]) == pytest.approx(94.09, abs=0.02)
    assert float(vacuum["landed_cost_usd"]) == pytest.approx(241.82, abs=0.02)
    assert float(vacuum["allocated_cost_per_unit_usd"]) == pytest.approx(41.82, abs=0.02)
    assert washer["landed_cost_per_unit_toman"] is not None
    assert float(washer["landed_cost_per_unit_toman"]) > 0


def test_finalize_shipment(client):
    sid = client.post("/api/shipments", json=PAYLOAD).json()["id"]
    r = client.post(f"/api/shipments/{sid}/finalize")
    assert r.status_code == 200, r.text
    f = r.json()
    assert f["status"] == "finalized"
    assert f["finalized_at"] is not None
    assert f["dollar_rate"] is not None and float(f["dollar_rate"]) > 0


def test_finalized_immutable(client):
    sid = client.post("/api/shipments", json=PAYLOAD).json()["id"]
    client.post(f"/api/shipments/{sid}/finalize")
    assert client.put(f"/api/shipments/{sid}", json={"name": "x"}).status_code == 400
    assert client.delete(f"/api/shipments/{sid}").status_code == 400
    assert client.post(f"/api/shipments/{sid}/finalize").status_code == 400


def test_margin_with_market_data(client):
    d = client.post("/api/shipments", json={
        "name": "ZZTEST Margin",
        "items": [{"title": "Vacuum", "sku": "BGL8PRO5", "quantity": 1,
                   "unit_purchase_price_usd": 200}],
        "costs": [],
    }).json()
    it = d["items"][0]
    assert it["market_min_toman"] is not None
    assert it["market_median_toman"] is not None
    assert it["margin_vs_min_pct"] is not None
    assert it["is_profitable"] in (True, False)
    expected = float(it["market_min_toman"]) - float(it["landed_cost_per_unit_toman"])
    assert float(it["margin_vs_min_toman"]) == pytest.approx(expected, abs=1)


def test_unknown_sku_no_crash(client):
    d = client.post("/api/shipments", json={
        "name": "ZZTEST Unknown",
        "items": [{"title": "Unknown", "sku": "NOPE-ABC", "quantity": 1,
                   "unit_purchase_price_usd": 100}],
        "costs": [],
    }).json()
    it = d["items"][0]
    assert it["market_min_toman"] is None
    assert it["margin_vs_min_pct"] is None
    assert it["is_profitable"] is None
    assert it["landed_cost_usd"] is not None


def test_empty_shipment(client):
    r = client.post("/api/shipments", json={"name": "ZZTEST empty", "items": [], "costs": []})
    assert r.status_code == 422


def test_zero_quantity(client):
    r = client.post("/api/shipments", json={
        "name": "ZZTEST qty0",
        "items": [{"title": "x", "quantity": 0, "unit_purchase_price_usd": 10}],
        "costs": [],
    })
    assert r.status_code == 422


def test_negative_price(client):
    r = client.post("/api/shipments", json={
        "name": "ZZTEST neg",
        "items": [{"title": "x", "quantity": 1, "unit_purchase_price_usd": -5}],
        "costs": [],
    })
    assert r.status_code == 422


def test_list_shipments(client):
    client.post("/api/shipments", json=PAYLOAD)
    client.post("/api/shipments", json=PAYLOAD)
    rows = client.get("/api/shipments").json()
    assert isinstance(rows, list)
    mine = [x for x in rows if x["name"] == "ZZTEST Integration"]
    assert len(mine) == 2
    assert all(k in mine[0] for k in ["id", "name", "status", "item_count", "total_value_usd"])


def test_get_nonexistent_404(client):
    assert client.get("/api/shipments/999999").status_code == 404


def test_detail_recalculates_live(client):
    sid = client.post("/api/shipments", json=PAYLOAD).json()["id"]
    r = client.get(f"/api/shipments/{sid}")
    assert r.status_code == 200
    assert r.json()["dollar_rate"] is not None and float(r.json()["dollar_rate"]) > 0


def test_cross_module_no_regression(client):
    """Existing endpoints still work (cross-module integration)."""
    assert client.get("/api/products").status_code == 200
    assert client.get("/api/margins").status_code == 200
    assert client.get("/api/market/overview").status_code == 200
    assert client.get("/api/system/health").status_code == 200
    assert client.get(f"/api/products/{WASHER_TOROB}").status_code == 200