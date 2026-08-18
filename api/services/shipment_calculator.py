"""Shipment landed-cost calculation engine.

Pure functions — no DB access, no I/O.

Unit conventions (IMPORTANT):
  - latest_prices.*_price_rial columns actually store TOMAN (see earlier
    bugfix: the /10 division was removed). So market_prices are TOMAN.
  - exchange_rate_rial is IRR per USD (Rial per USD). Toman per USD =
    exchange_rate_rial / 10.
  - landed_cost_toman = landed_cost_usd * (exchange_rate_rial / 10).
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class ShipmentItemCalc:
    """Input: a shipment item for calculation."""
    item_id: int
    title: str
    sku: str | None
    quantity: int
    unit_price_usd: Decimal


@dataclass
class ShipmentCostCalc:
    """Input: a shipment cost for calculation."""
    cost_type: str
    amount_usd: Decimal
    allocation_method: str = "by_value"


@dataclass
class ItemResult:
    """Output: calculated result for one item."""
    item_id: int
    title: str
    sku: str | None
    quantity: int
    unit_price_usd: Decimal
    total_value_usd: Decimal
    allocated_cost_usd: Decimal
    allocated_cost_per_unit_usd: Decimal
    landed_cost_per_unit_usd: Decimal
    landed_cost_per_unit_toman: Decimal | None
    # Market comparison (filled if market data available)
    market_min_toman: Decimal | None = None
    market_median_toman: Decimal | None = None
    margin_vs_min_toman: Decimal | None = None
    margin_vs_min_pct: float | None = None
    margin_vs_median_toman: Decimal | None = None
    margin_vs_median_pct: float | None = None
    is_profitable: bool | None = None


@dataclass
class ShipmentCalcResult:
    """Output: full shipment calculation."""
    total_value_usd: Decimal
    total_costs_usd: Decimal
    exchange_rate_rial: int | None
    items: list[ItemResult]


def calculate_shipment(
    items: list[ShipmentItemCalc],
    costs: list[ShipmentCostCalc],
    exchange_rate_rial: int | None,
    market_prices: dict[str, dict] | None = None,
) -> ShipmentCalcResult:
    """
    Calculate landed costs and margins for all items.

    Allocation: proportional to dollar value.
    Each item's share = (item_total_value / total_shipment_value) * total_costs

    market_prices: dict mapping SKU -> {"min_toman": int, "median_toman": int}
    (TOMAN values; latest_prices.*_price_rial are stored as Toman).
    """
    if not items:
        return ShipmentCalcResult(
            total_value_usd=Decimal("0"),
            total_costs_usd=Decimal("0"),
            exchange_rate_rial=exchange_rate_rial,
            items=[],
        )

    # Step 1: Calculate total values
    total_value_usd = sum(i.unit_price_usd * i.quantity for i in items)
    total_costs_usd = sum(c.amount_usd for c in costs)

    if total_value_usd == 0:
        # Edge case: all items have $0 price
        return ShipmentCalcResult(
            total_value_usd=Decimal("0"),
            total_costs_usd=total_costs_usd,
            exchange_rate_rial=exchange_rate_rial,
            items=[
                ItemResult(
                    item_id=i.item_id,
                    title=i.title,
                    sku=i.sku,
                    quantity=i.quantity,
                    unit_price_usd=i.unit_price_usd,
                    total_value_usd=Decimal("0"),
                    allocated_cost_usd=Decimal("0"),
                    allocated_cost_per_unit_usd=Decimal("0"),
                    landed_cost_per_unit_usd=i.unit_price_usd,
                    landed_cost_per_unit_toman=None,
                )
                for i in items
            ],
        )

    # Step 2: Allocate costs proportionally
    results = []
    for item in items:
        item_total_value = item.unit_price_usd * item.quantity

        # Proportional allocation
        allocation_ratio = item_total_value / total_value_usd
        allocated_total = total_costs_usd * allocation_ratio
        allocated_per_unit = allocated_total / item.quantity if item.quantity > 0 else Decimal("0")

        # Landed cost
        landed_usd = item.unit_price_usd + allocated_per_unit

        # Convert to Toman if exchange rate available
        landed_toman = None
        if exchange_rate_rial and exchange_rate_rial > 0:
            rate_toman_per_usd = Decimal(str(exchange_rate_rial)) / Decimal("10")
            landed_toman = (landed_usd * rate_toman_per_usd).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        result = ItemResult(
            item_id=item.item_id,
            title=item.title,
            sku=item.sku,
            quantity=item.quantity,
            unit_price_usd=item.unit_price_usd,
            total_value_usd=item_total_value,
            allocated_cost_usd=allocated_total,
            allocated_cost_per_unit_usd=allocated_per_unit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            landed_cost_per_unit_usd=landed_usd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            landed_cost_per_unit_toman=landed_toman,
        )

        # Step 3: Market comparison (if available)
        if market_prices and item.sku and item.sku in market_prices:
            mp = market_prices[item.sku]
            min_toman = mp.get("min_toman")
            median_toman = mp.get("median_toman")

            if landed_toman and min_toman:
                result.market_min_toman = Decimal(str(min_toman))
                margin_min = result.market_min_toman - landed_toman
                result.margin_vs_min_toman = margin_min
                result.margin_vs_min_pct = float(
                    (margin_min / landed_toman * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
                ) if landed_toman > 0 else None
                result.is_profitable = margin_min > 0

            if landed_toman and median_toman:
                result.market_median_toman = Decimal(str(median_toman))
                margin_median = result.market_median_toman - landed_toman
                result.margin_vs_median_toman = margin_median
                result.margin_vs_median_pct = float(
                    (margin_median / landed_toman * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
                ) if landed_toman > 0 else None

        results.append(result)

    return ShipmentCalcResult(
        total_value_usd=total_value_usd,
        total_costs_usd=total_costs_usd,
        exchange_rate_rial=exchange_rate_rial,
        items=results,
    )