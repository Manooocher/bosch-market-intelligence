"""Tests for statistics and currency modules."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from crawler.statistics import (
    compute_market_stats, calculate_seller_count, calculate_min_price,
    calculate_max_price, calculate_avg_price, calculate_median_price,
    calculate_price_spread, calculate_price_compression, calculate_price_dispersion,
    calculate_competition_score,
)
from crawler.currency import (
    toman_to_usd_cents, toman_to_usd, rial_to_toman,
)
from decimal import Decimal

import unittest


class TestStatistics(unittest.TestCase):
    def test_seller_count(self):
        self.assertEqual(calculate_seller_count([100, 200, 300]), 3)
        self.assertEqual(calculate_seller_count([]), 0)

    def test_min_max(self):
        self.assertEqual(calculate_min_price([500, 100, 300]), 100)
        self.assertEqual(calculate_max_price([500, 100, 300]), 500)

    def test_avg(self):
        self.assertEqual(calculate_avg_price([100, 200, 300]), 200)
        self.assertEqual(calculate_avg_price([100, 200, 301]), 200)

    def test_median(self):
        self.assertEqual(calculate_median_price([100, 200, 300]), 200)
        self.assertEqual(calculate_median_price([100, 200, 300, 400]), 250)
        self.assertEqual(calculate_median_price([100]), 100)
        self.assertEqual(calculate_median_price([]), 0)

    def test_spread(self):
        self.assertEqual(calculate_price_spread([100, 500]), 400)
        self.assertEqual(calculate_price_spread([100]), 0)
        self.assertEqual(calculate_price_spread([]), 0)

    def test_compression(self):
        c = calculate_price_compression([100.0, 100.0])
        self.assertAlmostEqual(c, 0.0, places=2)
        c2 = calculate_price_compression([100.0, 200.0])
        self.assertAlmostEqual(c2, 0.5, places=2)

    def test_dispersion(self):
        d = calculate_price_dispersion([100.0, 100.0])
        self.assertAlmostEqual(d, 0.0, places=2)
        d2 = calculate_price_dispersion([100.0, 200.0])
        self.assertAlmostEqual(d2, 0.6667, places=2)

    def test_competition_score(self):
        score = calculate_competition_score(10, 0.5, 0.3)
        self.assertGreater(score, 50)
        score2 = calculate_competition_score(1, 0.0, 0.0)
        self.assertLess(score2, 50)

    def test_compute_market_stats(self):
        prices = [1000000, 1500000, 2000000, 1200000, 1800000]
        stats = compute_market_stats(prices)
        self.assertEqual(stats.seller_count, 5)
        self.assertEqual(stats.min_price, 1000000)
        self.assertEqual(stats.max_price, 2000000)
        self.assertEqual(stats.avg_price, 1500000)
        self.assertEqual(stats.median_price, 1500000)
        self.assertGreater(stats.competition_score, 0)


class TestCurrency(unittest.TestCase):
    def test_toman_to_usd_cents(self):
        # 50,000,000 Toman = 500,000,000 Rial / 187,790 = 2662.55... USD
        cents = toman_to_usd_cents(50_000_000, 187790)
        self.assertEqual(cents, 266255)

    def test_toman_to_usd_decimal(self):
        usd = toman_to_usd(50_000_000, 187790)
        self.assertEqual(usd, Decimal("2662.55"))

    def test_rial_to_toman(self):
        self.assertEqual(rial_to_toman(187790), 18779)

    def test_zero_rate(self):
        self.assertEqual(toman_to_usd_cents(1000, 0), 0)
        self.assertEqual(toman_to_usd(1000, 0), Decimal("0"))

    def test_integer_arithmetic_no_float(self):
        # Verify no floating point issues
        cents = toman_to_usd_cents(39_500_000, 187790)
        self.assertEqual(cents, 210341)
        usd = toman_to_usd(39_500_000, 187790)
        self.assertEqual(usd, Decimal("2103.41"))


if __name__ == "__main__":
    unittest.main()
