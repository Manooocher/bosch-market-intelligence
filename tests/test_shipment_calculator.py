"""Tests for the shipment landed-cost calculation engine."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

import unittest
from decimal import Decimal

from api.services.shipment_calculator import (
    calculate_shipment, ShipmentItemCalc, ShipmentCostCalc,
)


def _item(i, sku, qty, price):
    return ShipmentItemCalc(item_id=i, title=f"Item {i}", sku=sku,
                            quantity=qty, unit_price_usd=Decimal(str(price)))


class TestShipmentCalculator(unittest.TestCase):
    def test_basic_allocation(self):
        """20×$450 + 10×$200, costs $2,300 → washer $544.09, vacuum $241.82."""
        items = [_item(1, "WASH", 20, 450), _item(2, "VAC", 10, 200)]
        costs = [ShipmentCostCalc(cost_type="shipping", amount_usd=Decimal("1500")),
                 ShipmentCostCalc(cost_type="customs", amount_usd=Decimal("800"))]
        res = calculate_shipment(items, costs, 185703)

        self.assertEqual(res.total_value_usd, Decimal("11000"))
        self.assertEqual(res.total_costs_usd, Decimal("2300"))

        washer = res.items[0]
        self.assertEqual(washer.allocated_cost_per_unit_usd, Decimal("94.09"))
        self.assertEqual(washer.landed_cost_per_unit_usd, Decimal("544.09"))

        vacuum = res.items[1]
        self.assertEqual(vacuum.allocated_cost_per_unit_usd, Decimal("41.82"))
        self.assertEqual(vacuum.landed_cost_per_unit_usd, Decimal("241.82"))

    def test_zero_costs(self):
        """No costs → landed = purchase price."""
        items = [_item(1, "A", 5, 100)]
        res = calculate_shipment(items, [], 100000)
        self.assertEqual(res.total_costs_usd, Decimal("0"))
        self.assertEqual(res.items[0].landed_cost_per_unit_usd, Decimal("100.00"))

    def test_single_item(self):
        """One item gets 100% of costs."""
        items = [_item(1, "A", 2, 100)]
        costs = [ShipmentCostCalc(cost_type="shipping", amount_usd=Decimal("50"))]
        res = calculate_shipment(items, costs, 100000)
        # 50/2 = 25 per unit; landed 125
        self.assertEqual(res.items[0].allocated_cost_per_unit_usd, Decimal("25.00"))
        self.assertEqual(res.items[0].landed_cost_per_unit_usd, Decimal("125.00"))

    def test_zero_quantity_no_divzero(self):
        """quantity=0 should not cause division by zero (not created via API but defensive)."""
        items = [_item(1, "A", 0, 100)]
        res = calculate_shipment(items, [], 100000)
        self.assertEqual(res.items[0].allocated_cost_per_unit_usd, Decimal("0.00"))

    def test_margin_profitable(self):
        """landed 70M toman, market min 85M → margin +15M, +21.4%."""
        items = [_item(1, "WASH", 1, 3770)]  # 3770 USD × 18570.3 = ~70.01M toman
        res = calculate_shipment(items, [], 185703,
                                 market_prices={"WASH": {"min_toman": 85_000_000, "median_toman": 90_000_000}})
        it = res.items[0]
        self.assertTrue(it.is_profitable)
        self.assertGreater(it.margin_vs_min_toman, Decimal("0"))

    def test_margin_unprofitable(self):
        """landed 150M toman, market min 139M → margin -11M."""
        # 150M toman / 18570.3 = ~8077 USD
        items = [_item(1, "WASH", 1, 8077)]
        res = calculate_shipment(items, [], 185703,
                                 market_prices={"WASH": {"min_toman": 139_000_000, "median_toman": 145_000_000}})
        it = res.items[0]
        self.assertFalse(it.is_profitable)
        self.assertLess(it.margin_vs_min_toman, Decimal("0"))

    def test_no_market_data(self):
        """Item with no matching SKU → all margin fields None."""
        items = [_item(1, "NOPE", 1, 100)]
        res = calculate_shipment(items, [], 185703, market_prices={"OTHER": {"min_toman": 1000, "median_toman": 2000}})
        it = res.items[0]
        self.assertIsNone(it.market_min_toman)
        self.assertIsNone(it.margin_vs_min_pct)
        self.assertIsNone(it.is_profitable)

    def test_dollar_rate_conversion(self):
        """$544.09 × 187790 ≈ correct toman value (using unrounded landed)."""
        # rate 187790 -> toman/usd = 18779
        items = [_item(1, "WASH", 20, 450), _item(2, "VAC", 10, 200)]
        costs = [ShipmentCostCalc(cost_type="shipping", amount_usd=Decimal("1500")),
                 ShipmentCostCalc(cost_type="customs", amount_usd=Decimal("800"))]
        res = calculate_shipment(items, costs, 187790)
        washer = res.items[0]
        # Calculator converts from UNROUNDED landed usd:
        #   landed_usd = 450 + (9000/11000)*2300/20 = 544.0909...
        landed_usd = Decimal("450") + ((Decimal("9000") / Decimal("11000")) * Decimal("2300") / Decimal("20"))
        expected = (landed_usd * Decimal("18779")).quantize(Decimal("1"), rounding="ROUND_HALF_UP")
        self.assertEqual(washer.landed_cost_per_unit_toman, expected)
        # sanity: approx 10.2M toman
        self.assertGreater(washer.landed_cost_per_unit_toman, Decimal("10000000"))
        self.assertLess(washer.landed_cost_per_unit_toman, Decimal("11000000"))

    def test_empty_items(self):
        res = calculate_shipment([], [], 100000)
        self.assertEqual(res.total_value_usd, Decimal("0"))
        self.assertEqual(res.items, [])

    def test_zero_total_value(self):
        items = [_item(1, "A", 5, 0)]
        costs = [ShipmentCostCalc(cost_type="shipping", amount_usd=Decimal("100"))]
        res = calculate_shipment(items, costs, 100000)
        # all zero price -> landed = unit price (0), no allocation
        self.assertEqual(res.total_value_usd, Decimal("0"))
        self.assertEqual(res.items[0].landed_cost_per_unit_usd, Decimal("0"))


if __name__ == "__main__":
    unittest.main()