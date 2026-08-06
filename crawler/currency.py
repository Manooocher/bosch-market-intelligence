"""Exchange rate fetcher with Decimal arithmetic.

Fetches USDT/IRT rate from Tabdeal API.
Uses Decimal for all conversions — never float.
"""

import json
import logging
import os
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

TABDEAL_API_URL = os.getenv(
    "TABDEAL_API_URL",
    "https://api1.tabdeal.org/r/api/v1/depth?symbol=USDTIRT&limit=1"
)

# Fallback rate: ~187,790 IRR per USDT (August 2026 estimate)
FALLBACK_RIAL_PER_USDT = Decimal("187790")


@dataclass
class RialRate:
    """Exchange rate with provenance."""
    value: int          # IRR per USDT, integer
    source: str         # "tabdeal", "fallback"
    timestamp: str      # ISO timestamp


class ExchangeRateFetcher:
    """Fetches USDT/IRT rate from Tabdeal API.

    Uses Decimal for all monetary calculations.
    Fetches once per monitoring cycle.
    """

    def __init__(self, http_client):
        self.client = http_client
        self._cached_rate: RialRate | None = None

    def fetch(self) -> RialRate:
        """Fetch current exchange rate. Returns integer Rials per USDT."""
        if self._cached_rate:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(self._cached_rate.timestamp)
            if age.total_seconds() < 3600:  # Cache for 1 hour
                return self._cached_rate

        try:
            resp = self.client.request(TABDEAL_API_URL)
            if not resp or not resp.success:
                return self._fallback("request_failed")

            data = resp.data
            if not data:
                return self._fallback("empty_response")

            asks = data.get("asks", [])
            if not asks or not asks[0]:
                return self._fallback("no_asks")

            # asks[0][0] is a string like "187790.0000000000000000"
            raw_str = str(asks[0][0])
            rial_decimal = Decimal(raw_str).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            rial_rate = int(rial_decimal)

            if rial_rate <= 0:
                return self._fallback("invalid_rate")

            now = datetime.now(timezone.utc).isoformat()
            rate = RialRate(value=rial_rate, source="tabdeal", timestamp=now)
            self._cached_rate = rate
            logger.info(f"Exchange rate: {rial_rate} IRR/USDT (source: tabdeal)")
            return rate

        except Exception as e:
            logger.warning(f"Tabdeal API failed: {e}")
            return self._fallback(str(e))

    def _fallback(self, reason: str) -> RialRate:
        """Return cached or default rate on failure."""
        if self._cached_rate:
            logger.warning(f"Using cached rate {self._cached_rate.value} (reason: {reason})")
            return self._cached_rate

        logger.warning(f"Using fallback rate {FALLBACK_RIAL_PER_USDT} (reason: {reason})")
        now = datetime.now(timezone.utc).isoformat()
        return RialRate(
            value=int(FALLBACK_RIAL_PER_USDT),
            source="fallback",
            timestamp=now,
        )


def toman_to_usd_cents(toman_price: int, rial_rate: int) -> int:
    """Convert Toman price to USD cents using integer arithmetic.

    Toman = 10 Rial.
    rial_rate = IRR per USDT.
    Returns USD cents (2 decimal places as integer).
    """
    if rial_rate <= 0:
        return 0
    rial = toman_price * 10
    cents = (Decimal(str(rial)) * Decimal("100") / Decimal(str(rial_rate)))
    return int(cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def toman_to_usd(toman_price: int, rial_rate: int) -> Decimal:
    """Convert Toman price to USD using Decimal.

    Returns USD as a Decimal with 2 decimal places.
    """
    if rial_rate <= 0:
        return Decimal("0")
    rial = toman_price * 10
    usd = Decimal(str(rial)) / Decimal(str(rial_rate))
    return usd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def rial_to_toman(rial: int) -> int:
    """Convert Rial to Toman (divide by 10, integer)."""
    return rial // 10
