"""Centralized crawler configuration.

All crawler settings are defined here as dataclasses.
Environment variables override defaults.
No other module should contain configuration constants.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


# ── Base Paths ──────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
COOKIE_DIR = DATA_DIR / "cookies"
PROXY_HEALTH_DB = DATA_DIR / "proxy_health.db"
METRICS_FILE = DATA_DIR / "metrics.json"
RECOVERY_OUTPUT_DIR = DATA_DIR / "recovered"
DAILY_OUTPUT_DIR = DATA_DIR / "daily"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(COOKIE_DIR, exist_ok=True)
os.makedirs(RECOVERY_OUTPUT_DIR, exist_ok=True)
os.makedirs(DAILY_OUTPUT_DIR, exist_ok=True)


# ── Configuration Dataclasses ───────────────────────────────────────────────

@dataclass
class TorobEndpoints:
    """Torob API endpoint URLs."""
    api_base: str = "https://api.torob.com/v4"
    search: str = ""
    details: str = ""
    brand_list: str = ""
    category_suggest: str = ""
    homepage: str = "https://torob.com/"

    def __post_init__(self):
        if not self.search:
            self.search = f"{self.api_base}/base-product/search/"
        if not self.details:
            self.details = f"{self.api_base}/base-product/details/"
        if not self.brand_list:
            self.brand_list = f"{self.api_base}/brand/list/"
        if not self.category_suggest:
            self.category_suggest = f"{self.api_base}/category/suggestion/"


@dataclass
class RetryConfig:
    """Retry and backoff configuration."""
    max_retries: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: float = 0.3

    # Per-error retry settings
    retry_on_429: bool = True
    retry_on_5xx: bool = True
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True
    max_429_retries: int = 3
    max_5xx_retries: int = 2
    max_timeout_retries: int = 2


@dataclass
class TimeoutConfig:
    """Request timeout configuration."""
    connect: float = 10.0
    read: float = 30.0
    total: float = 60.0


@dataclass
class RateProfile:
    """Rate limiting profile for a specific crawler mode."""
    name: str = "default"
    requests_per_batch: int = 10
    delay_min: float = 2.0
    delay_max: float = 4.0
    pause_between_batches_min: float = 30.0
    pause_between_batches_max: float = 45.0
    long_pause_interval: int = 50
    long_pause_min: float = 90.0
    long_pause_max: float = 120.0


@dataclass
class ProxyConfig:
    """Proxy-Cheap gateway configuration."""
    enabled: bool = False
    username: str = ""
    password: str = ""
    country: str = "IR"
    gateway_host: str = "thehub.proxy-cheap.com"
    gateway_port: int = 8080

    # Session management
    rotate_every_recovery: int = 15
    rotate_every_monitor: int = 50
    rotate_every_discovery: int = 30
    session_max_lifetime_minutes: int = 120
    session_lifetime_recovery_minutes: int = 3

    # Health
    health_check_interval: int = 10
    unhealthy_threshold: float = 40.0
    quarantine_duration_seconds: int = 900
    quarantine_burned_duration_seconds: int = 14400

    @classmethod
    def from_env(cls) -> "ProxyConfig":
        return cls(
            enabled=os.getenv("TOROB_PROXY_ENABLED", "false").lower() == "true",
            username=os.getenv("TOROB_PROXY_USER", ""),
            password=os.getenv("TOROB_PROXY_PASS", ""),
            country=os.getenv("TOROB_PROXY_COUNTRY", "IR"),
        )


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    monitoring_window: int = 20
    cooldown_seconds: int = 120
    half_open_max_requests: int = 1
    success_threshold_half_open: int = 1


@dataclass
class SchedulerConfig:
    """Request scheduler configuration."""
    max_concurrent_batches: int = 1
    adaptive_slowdown_enabled: bool = True
    slowdown_factor: float = 1.5
    slowdown_trigger_error_rate: float = 0.3


@dataclass
class CrawlerConfig:
    """Master crawler configuration.

    Composes all sub-configurations.
    Single source of truth for all crawler settings.
    """
    endpoints: TorobEndpoints = field(default_factory=TorobEndpoints)
    retry: RetryConfig = field(default_factory=RetryConfig)
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)

    # Rate profiles per mode
    rate_profiles: dict = field(default_factory=lambda: {
        "recovery": RateProfile(
            name="recovery",
            requests_per_batch=10,
            delay_min=2.0, delay_max=4.0,
            pause_between_batches_min=30.0, pause_between_batches_max=45.0,
            long_pause_interval=50, long_pause_min=90.0, long_pause_max=120.0,
        ),
        "monitor": RateProfile(
            name="monitor",
            requests_per_batch=50,
            delay_min=1.0, delay_max=2.0,
            pause_between_batches_min=30.0, pause_between_batches_max=45.0,
            long_pause_interval=80, long_pause_min=60.0, long_pause_max=90.0,
        ),
        "discovery": RateProfile(
            name="discovery",
            requests_per_batch=25,
            delay_min=5.0, delay_max=8.0,
            pause_between_batches_min=45.0, pause_between_batches_max=60.0,
            long_pause_interval=40, long_pause_min=60.0, long_pause_max=90.0,
        ),
    })

    # Business constants
    page_size: int = 48
    bosch_brand_id: int = 73
    bosch_queries: list = field(default_factory=lambda: ["بوش", "bosch"])

    @classmethod
    def from_env(cls) -> "CrawlerConfig":
        return cls(proxy=ProxyConfig.from_env())

    def get_rate_profile(self, mode: str) -> RateProfile:
        return self.rate_profiles.get(mode, self.rate_profiles["monitor"])
