"""Services package — business logic layer."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class MarginResult:
    nabkade_price_toman: int = 0
    nabkade_price_usd_cents: int = 0
    market_min_price_toman: int = 0
    market_median_price_toman: int = 0
    margin_vs_min_toman: int = 0
    margin_vs_median_toman: int = 0
    margin_vs_min_pct: float = 0.0
    margin_vs_median_pct: float = 0.0
    is_profitable: bool = False
    data_freshness: str = "unknown"


def parse_toman(price_str: str) -> int:
    """Parse Toman price from string format like '127,300,000'."""
    if not price_str:
        return 0
    cleaned = price_str.replace(",", "").replace("،", "").strip()
    persian = "۰۱۲۳۴۵۶۷۸۹"
    ascii_d = "0123456789"
    for p, a in zip(persian, ascii_d):
        cleaned = cleaned.replace(p, a)
    try:
        return int(cleaned)
    except ValueError:
        return 0


def toman_to_usd_cents(toman_price: int, rial_rate: int) -> int:
    if rial_rate <= 0 or toman_price <= 0:
        return 0
    rial = toman_price * 10
    cents = (Decimal(str(rial)) * Decimal("100") / Decimal(str(rial_rate)))
    return int(cents.quantize(Decimal("1")))


class FreshnessAnalyzer:
    @staticmethod
    def analyze(fetched_at: datetime | None) -> str:
        if not fetched_at:
            return "unknown"
        age = datetime.now(timezone.utc) - fetched_at
        if age < timedelta(hours=24):
            return "fresh"
        if age < timedelta(hours=96):
            return "acceptable"
        return "stale"


class MarginCalculator:
    def __init__(self, exchange_rate: int):
        self._rate = exchange_rate

    def calculate(self, nabkade_price_toman: int, market_min_rial: int, market_median_rial: int) -> dict:
        if nabkade_price_toman <= 0 or market_min_rial <= 0 or self._rate <= 0:
            return {"margin_vs_min_toman": 0, "margin_vs_median_toman": 0, "margin_vs_min_pct": 0.0, "margin_vs_median_pct": 0.0, "is_profitable": False}

        nabkade_rial = nabkade_price_toman * 10
        nabkade_usd_cents = int((Decimal(str(nabkade_rial)) * Decimal("100") / Decimal(str(self._rate))).quantize(Decimal("1")))
        # Market prices are already stored in Toman (despite the _rial column name)
        min_market_toman = market_min_rial
        median_market_toman = market_median_rial
        margin_min = nabkade_price_toman - min_market_toman
        margin_median = nabkade_price_toman - median_market_toman
        pct_min = float(Decimal(str(margin_min)) / Decimal(str(nabkade_price_toman)) * 100) if nabkade_price_toman > 0 else 0.0
        pct_median = float(Decimal(str(margin_median)) / Decimal(str(nabkade_price_toman)) * 100) if nabkade_price_toman > 0 else 0.0
        return {"nabkade_price_toman": nabkade_price_toman, "nabkade_price_usd_cents": nabkade_usd_cents, "market_min_price_toman": min_market_toman, "market_median_price_toman": median_market_toman, "margin_vs_min_toman": margin_min, "margin_vs_median_toman": margin_median, "margin_vs_min_pct": round(pct_min, 1), "margin_vs_median_pct": round(pct_median, 1), "is_profitable": margin_min > 0}