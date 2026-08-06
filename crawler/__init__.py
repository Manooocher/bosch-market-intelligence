"""Crawler Infrastructure — Production package.

Provides:
- CrawlerConfig: centralized configuration
- HttpClient: single HTTP implementation
- FingerprintManager: browser identity
- ProxyManager: Proxy-Cheap gateway
- ProxyHealthStore: persistent health tracking
- CircuitBreaker: failure prevention
- RetryPolicy: error-specific retry logic
- RequestScheduler: batch/delay/rotation scheduling
- MetricsCollector: observability
- TorobCrawler: Torob API adapter

All consumers (Recovery, Discovery, Monitor) MUST use this package.
"""

from crawler.config import CrawlerConfig, ProxyConfig, RateProfile
from crawler.http_client import HttpClient, Response
from crawler.fingerprint import FingerprintManager
from crawler.proxy import ProxyManager, ProxySession
from crawler.proxy_health import ProxyHealthStore
from crawler.circuit_breaker import CircuitBreaker
from crawler.retry import RetryPolicy, classify_error
from crawler.scheduler import RequestScheduler, WorkItem, BatchResult
from crawler.metrics import MetricsCollector
from crawler.torob import TorobCrawler, CrawlerResponse
