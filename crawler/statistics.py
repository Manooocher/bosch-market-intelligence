"""Market statistics calculation.

Pure functions — no I/O, no state.
All inputs are integers (Rial prices).
All outputs are integers or deterministic floats in [0, 1].
"""

import math
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class MarketStats:
    """Computed statistics for a product's market."""
    seller_count: int
    min_price: int
    max_price: int
    avg_price: int
    median_price: int
    price_spread: int
    price_compression: float
    price_dispersion: float
    competition_score: int  # 0-100


def calculate_seller_count(prices: list[int]) -> int:
    """Number of distinct sellers (based on price count)."""
    return len(prices)


def calculate_min_price(prices: list[int]) -> int:
    return min(prices) if prices else 0


def calculate_max_price(prices: list[int]) -> int:
    return max(prices) if prices else 0


def calculate_avg_price(prices: list[int]) -> int:
    """Integer mean — rounded to nearest integer."""
    if not prices:
        return 0
    return sum(prices) // len(prices)


def calculate_median_price(prices: list[int]) -> int:
    """Integer median — middle value of sorted list."""
    if not prices:
        return 0
    s = sorted(prices)
    n = len(s)
    if n % 2 == 0:
        return (s[n // 2 - 1] + s[n // 2]) // 2
    return s[n // 2]


def calculate_price_spread(prices: list[int]) -> int:
    """Absolute spread: max - min."""
    if len(prices) < 2:
        return 0
    return max(prices) - min(prices)


def calculate_price_compression(prices: list[float]) -> float:
    """1 - (min / max). Range [0, 1]. Higher = more compressed."""
    if not prices or len(prices) < 2:
        return 0.0
    mn, mx = min(prices), max(prices)
    if mx <= 0:
        return 0.0
    return 1.0 - (mn / mx)


def calculate_price_dispersion(prices: list[float]) -> float:
    """(max - min) / avg. Normalized to [0, 1]. Higher = wider spread."""
    if not prices or len(prices) < 2:
        return 0.0
    mn, mx = min(prices), max(prices)
    avg = sum(prices) / len(prices)
    if avg <= 0:
        return 0.0
    dispersion = (mx - mn) / avg
    return min(1.0, dispersion)


def calculate_competition_score(
    seller_count: int,
    price_compression: float,
    price_dispersion: float,
) -> int:
    """Competition score 0-100.

    Components:
    - seller_count_score: min(1.0, count/10) — max at 10+ sellers
    - compression_score: price_compression [0,1]
    - dispersion_score: 1 - min(1.0, dispersion/0.5) — less dispersion = less competition
    """
    seller_score = min(1.0, seller_count / 10.0)
    compression_score = price_compression
    dispersion_score = 1.0 - min(1.0, price_dispersion / 0.5)

    raw = (seller_score + compression_score + dispersion_score) / 3.0 * 100.0
    return max(0, min(100, int(round(raw))))


def compute_market_stats(prices_rial: list[int]) -> MarketStats:
    """Compute all market statistics from a list of Rial prices."""
    count = calculate_seller_count(prices_rial)
    mn = calculate_min_price(prices_rial)
    mx = calculate_max_price(prices_rial)
    avg = calculate_avg_price(prices_rial)
    med = calculate_median_price(prices_rial)
    spread = calculate_price_spread(prices_rial)

    prices_float = [float(p) for p in prices_rial]
    compression = calculate_price_compression(prices_float)
    dispersion = calculate_price_dispersion(prices_float)
    score = calculate_competition_score(count, compression, dispersion)

    return MarketStats(
        seller_count=count,
        min_price=mn,
        max_price=mx,
        avg_price=avg,
        median_price=med,
        price_spread=spread,
        price_compression=round(compression, 4),
        price_dispersion=round(dispersion, 4),
        competition_score=score,
    )
