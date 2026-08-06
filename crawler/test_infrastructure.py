"""Integration test for crawler infrastructure.

Verifies all modules load and wire together correctly.
Does NOT make any HTTP requests.
"""

import sys
import os
import tempfile
sys.stdout.reconfigure(encoding="utf-8")

from crawler.config import CrawlerConfig, RateProfile
from crawler.fingerprint import FingerprintManager
from crawler.proxy_health import ProxyHealthStore, ProxySessionRecord
from crawler.proxy import ProxyManager
from crawler.circuit_breaker import CircuitBreaker, State
from crawler.retry import RetryPolicy, classify_error, ErrorCategory
from crawler.scheduler import RequestScheduler, WorkItem
from crawler.metrics import MetricsCollector
from crawler.http_client import HttpClient
from crawler.torob import TorobCrawler


def _make_db():
    """Create a temp DB path that doesn't exist."""
    path = os.path.join(tempfile.gettempdir(), f"test_{os.getpid()}_{id({})}.db")
    if os.path.exists(path):
        os.unlink(path)
    return path


def _cleanup(path):
    try:
        if os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass


def test_config():
    config = CrawlerConfig()
    assert config.page_size == 48
    assert config.bosch_brand_id == 73
    profile = config.get_rate_profile("recovery")
    assert profile.name == "recovery"
    assert profile.requests_per_batch == 10
    print("  Config: OK")


def test_fingerprint():
    fm = FingerprintManager()
    headers = fm.get_headers()
    assert "User-Agent" in headers
    assert "Chrome/" in headers["User-Agent"]
    fm.rotate_identity()
    headers2 = fm.get_headers()
    assert headers["User-Agent"] != headers2["User-Agent"]
    print("  Fingerprint: OK")


def test_proxy_health():
    db_path = _make_db()
    try:
        store = ProxyHealthStore(db_path)
        record = ProxySessionRecord(session_id="test_1", created_at="2026-01-01")
        store.upsert(record)
        store.record_success("test_1", 150)
        store.record_error("test_1", "490")
        got = store.get("test_1")
        assert got is not None, "Record not found after upsert"
        assert got.request_count == 2, f"Expected 2, got {got.request_count}"
        assert got.success_count == 1, f"Expected success=1, got {got.success_count}"
        assert got.error_490_count == 1, f"Expected 490=1, got {got.error_490_count}"
        assert got.total_latency_ms == 150
        summary = store.health_summary()
        assert summary["total"] == 1
        store.close()
        print("  ProxyHealth: OK")
    finally:
        _cleanup(db_path)


def test_proxy_manager():
    db_path = _make_db()
    try:
        from crawler.config import ProxyConfig
        store = ProxyHealthStore(db_path)
        config = ProxyConfig(enabled=False)
        pm = ProxyManager(config, store)
        session = pm.create_session("test")
        assert session.session_id == "direct"
        assert session.proxy_url == ""
        pm.record_success(session.session_id, 100)
        print("  ProxyManager: OK")
        store.close()
    finally:
        _cleanup(db_path)


def test_circuit_breaker():
    cb = CircuitBreaker()
    assert cb.state == State.CLOSED
    assert cb.allow_request() is True
    for _ in range(5):
        cb.record_failure()
    assert cb.state == State.OPEN
    assert cb.allow_request() is False
    cb.reset()
    assert cb.state == State.CLOSED
    print("  CircuitBreaker: OK")


def test_retry_policy():
    rp = RetryPolicy()
    assert rp.should_retry(ErrorCategory.SUCCESS, 0) is False
    assert rp.should_retry(ErrorCategory.BLOCKED_490, 0) is True  # rotate and retry
    assert rp.should_retry(ErrorCategory.RATE_LIMITED_429, 0) is True
    assert rp.should_retry(ErrorCategory.SERVER_ERROR, 0) is True
    assert rp.needs_rotation(ErrorCategory.BLOCKED_490) is True
    assert rp.needs_rotation(ErrorCategory.SERVER_ERROR) is False
    print("  RetryPolicy: OK")


def test_error_classifier():
    c = classify_error(status_code=490)
    assert c.category == ErrorCategory.BLOCKED_490
    c2 = classify_error(status_code=200)
    assert c2.category == ErrorCategory.SUCCESS
    c3 = classify_error(exception=TimeoutError("timeout"))
    assert c3.category == ErrorCategory.TIMEOUT
    print("  ErrorClassifier: OK")


def test_scheduler():
    db_path = _make_db()
    try:
        from crawler.config import ProxyConfig
        store = ProxyHealthStore(db_path)
        config = ProxyConfig(enabled=False)
        pm = ProxyManager(config, store)
        profile = RateProfile(name="test", requests_per_batch=5)
        sched = RequestScheduler(profile, pm)
        batches = sched.create_batches(list(range(12)))
        assert len(batches) == 3
        assert len(batches[0]) == 5
        assert len(batches[2]) == 2
        print("  Scheduler: OK")
        store.close()
    finally:
        _cleanup(db_path)


def test_metrics():
    m = MetricsCollector()
    m.record_request("test", 200, 150, "sess1", 0)
    m.record_request("test", 490, 200, "sess1", 1)
    m.record_proxy_rotation("scheduled")
    s = m.get_summary()
    assert s["requests"]["requests_total"] == 2
    assert s["requests"]["error_490"] == 1
    assert s["requests"]["proxy_rotations"] == 1
    print("  Metrics: OK")


def test_full_integration():
    db_path = _make_db()
    try:
        config = CrawlerConfig()
        health_store = ProxyHealthStore(db_path)
        proxy_manager = ProxyManager(config.proxy, health_store)
        fingerprint = FingerprintManager()
        circuit_breaker = CircuitBreaker(config.circuit_breaker)
        retry_policy = RetryPolicy(config.retry)
        metrics = MetricsCollector()

        client = HttpClient(
            config=config,
            proxy_manager=proxy_manager,
            fingerprint=fingerprint,
            circuit_breaker=circuit_breaker,
            retry_policy=retry_policy,
            metrics=metrics,
            mode="test",
        )

        crawler = TorobCrawler(client, config)
        assert crawler.config.page_size == 48

        profile = config.get_rate_profile("recovery")
        scheduler = RequestScheduler(profile, proxy_manager)

        m = MetricsCollector()
        m.record_request("test", 200, 1234, "sess1", 0)
        m.record_request("test", 490, 500, "sess1", 1)
        summary = m.get_summary()
        assert summary["requests"]["requests_total"] == 2

        client.close()
        health_store.close()
        print("  Full Integration: OK")
    finally:
        _cleanup(db_path)


if __name__ == "__main__":
    print("Crawler Infrastructure Integration Tests\n")
    test_config()
    test_fingerprint()
    test_proxy_health()
    test_proxy_manager()
    test_circuit_breaker()
    test_retry_policy()
    test_error_classifier()
    test_scheduler()
    test_metrics()
    test_full_integration()
    print("\nAll tests passed!")
