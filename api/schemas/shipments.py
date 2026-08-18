"""Pydantic schemas for the Shipment module (Phase 7)."""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field


class ShipmentItemCreate(BaseModel):
    title: str = Field(min_length=1)
    sku: Optional[str] = None
    quantity: int = Field(ge=1)
    unit_purchase_price_usd: float = Field(ge=0)
    nabkade_product_id: Optional[str] = None
    torob_product_id: Optional[str] = None


class ShipmentCostCreate(BaseModel):
    cost_type: Literal["shipping", "customs", "insurance", "warehouse", "handling", "other"]
    description: Optional[str] = None
    amount_usd: float = Field(ge=0)


class ShipmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    notes: Optional[str] = None
    items: list[ShipmentItemCreate] = Field(min_length=1)
    costs: list[ShipmentCostCreate] = []


class ShipmentUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[list[ShipmentItemCreate]] = None
    costs: Optional[list[ShipmentCostCreate]] = None


class ItemResultOut(BaseModel):
    id: int
    title: str
    sku: Optional[str]
    nabkade_product_id: Optional[str]
    torob_product_id: Optional[str]
    quantity: int
    unit_purchase_price_usd: Decimal
    total_value_usd: Decimal = Decimal("0")
    allocated_cost_usd: Decimal = Decimal("0")
    allocated_cost_per_unit_usd: Decimal = Decimal("0")
    landed_cost_usd: Decimal = Decimal("0")
    landed_cost_per_unit_toman: Optional[Decimal] = None
    # Market comparison
    market_min_toman: Optional[Decimal] = None
    market_median_toman: Optional[Decimal] = None
    margin_vs_min_toman: Optional[Decimal] = None
    margin_vs_min_pct: Optional[float] = None
    margin_vs_median_toman: Optional[Decimal] = None
    margin_vs_median_pct: Optional[float] = None
    is_profitable: Optional[bool] = None


class ShipmentCostOut(BaseModel):
    id: int
    cost_type: str
    description: Optional[str]
    amount_usd: Decimal


class ShipmentListRow(BaseModel):
    id: int
    name: str
    status: str
    created_at: Optional[datetime]
    finalized_at: Optional[datetime]
    item_count: int = 0
    total_value_usd: Decimal = Decimal("0")
    total_costs_usd: Decimal = Decimal("0")


class ShipmentDetailOut(BaseModel):
    id: int
    name: str
    status: str
    notes: Optional[str]
    dollar_rate: Optional[Decimal]
    created_at: Optional[datetime]
    finalized_at: Optional[datetime]
    total_value_usd: Decimal
    total_costs_usd: Decimal
    items: list[ItemResultOut]
    costs: list[ShipmentCostOut]
    message: Optional[str] = None
