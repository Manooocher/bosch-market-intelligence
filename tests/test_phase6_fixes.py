"""Tests for Phase 6.5 fixes: price parser validation + outlier price filter."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

import unittest

from crawler.seller_parser import parse_price, MIN_VALID_PRICE_RIAL, MAX_VALID_PRICE_RIAL
from crawler.statistics import filter_outlier_prices


class TestParsePrice(unittest.TestCase):
    def test_normal_price(self):
        self.assertEqual(parse_price("15000000"), 15_000_000)
        self.assertEqual(parse_price(15000000), 15_000_000)
        self.assertEqual(parse_price("15,000,000"), 15_000_000)

    def test_persian_digits(self):
        # "۱۵۰۰۰۰۰۰" are Persian digits
        self.assertEqual(parse_price("۱۵۰۰۰۰۰۰"), 15_000_000)

    def test_reject_negative_and_zero(self):
        self.assertIsNone(parse_price(0))
        self.assertIsNone(parse_price(-5))

    def test_reject_suspicious_low(self):
        self.assertIsNone(parse_price("1000"))
        self.assertIsNone(parse_price("50000"))

    def test_boundary_min(self):
        # Exactly MIN_VALID_PRICE_RIAL is allowed (reject is strictly-below).
        self.assertEqual(parse_price(str(MIN_VALID_PRICE_RIAL)), MIN_VALID_PRICE_RIAL)

    def test_reject_unrealistically_high(self):
        self.assertIsNone(parse_price(str(MAX_VALID_PRICE_RIAL + 1)))

    def test_none_and_empty(self):
        self.assertIsNone(parse_price(None))
        self.assertIsNone(parse_price(""))


class TestFilterOutlierPrices(unittest.TestCase):
    def test_drops_low_outlier(self):
        prices = [37_000_000, 36_500_000, 38_000_000, 16, 35_000_000]
        filtered = filter_outlier_prices(prices)
        self.assertNotIn(16, filtered)
        self.assertIn(38_000_000, filtered)

    def test_clean_list_unchanged(self):
        clean = [1_000_000, 1_100_000, 1_200_000, 900_000]
        self.assertEqual(filter_outlier_prices(clean), clean)

    def test_fewer_than_three_unchanged(self):
        tiny = [10_000_000, 15]
        self.assertEqual(filter_outlier_prices(tiny), tiny)


if __name__ == "__main__":
    unittest.main()