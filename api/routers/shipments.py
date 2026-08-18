"""Shipments router — CRUD + finalize for the landed-cost module (Phase 7).

Unit conventions:
  - latest_prices.*_price_rial columns store TOMAN (see earlier bugfix: /10
    division removed), so market prices are used directly as Toman.
  - Dollar rate = monitor_runs.exchange_rate_rial (IRR per USD). Toman per USD
    = exchange_rate_rial / 10.
"""
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_session
from db.models import Shipment, ShipmentItem, ShipmentCost, LatestPrice, MonitorRun

from api.schemas.shipments import (
    ShipmentCreate, ShipmentUpdate, ShipmentDetailOut, ShipmentListRow,
    ShipmentCostOut, ItemResultOut,
)
from api.services.shipment_calculator import (
    calculate_shipment, ShipmentItemCalc, ShipmentCostCalc,
)

logger = logging.getLogger("api.routers.shipments")
router = APIRouter(prefix="/api/shipments", tags=["shipments"])

# Cost-type labels used by frontend (mirror the DB CHECK constraint).
COST_TYPES = ["shipping", "customs", "insurance", "warehouse", "handling", "other"]


async def get_exchange_rate(session: AsyncSession) -> int | None:
    """Latest exchange rate (IRR per USD) from the most recent monitor run."""
    stmt = (
        select(MonitorRun.exchange_rate_rial)
        .where(MonitorRun.exchange_rate_rial > 0)
        .order_by(MonitorRun.id.desc())
        .limit(1)
    )
    return await session.scalar(stmt)


async def get_market_prices(session: AsyncSession, skus: list[str]) -> dict:
    """min/median market prices (TOMAN) from latest_prices, matched by SKU."""
    if not skus:
        return {}
    stmt = select(LatestPrice).where(LatestPrice.sku.in_(skus))
    result = await session.execute(stmt)
    prices: dict[str, dict] = {}
    for lp in result.scalars().all():
        if lp.sku and lp.min_price_rial and lp.median_price_rial:
            # *_price_rial columns store Toman
            prices[lp.sku] = {
                "min_toman": lp.min_price_rial,
                "median_toman": lp.median_price_rial,
            }
    return prices


def _item_to_calc(item: ShipmentItem) -> ShipmentItemCalc:
    return ShipmentItemCalc(
        item_id=item.id,
        title=item.title,
        sku=item.sku,
        quantity=item.quantity,
        unit_price_usd=Decimal(str(item.unit_purchase_price_usd)),
    )


def _cost_to_calc(cost: ShipmentCost) -> ShipmentCostCalc:
    return ShipmentCostCalc(
        cost_type=cost.cost_type,
        amount_usd=Decimal(str(cost.amount_usd)),
    )


def _calc_to_item_result(item: ShipmentItem, calc) -> dict:
    """Merge persisted item fields with calculator outputs for response."""
    return {
        "id": item.id,
        "title": item.title,
        "sku": item.sku,
        "nabkade_product_id": item.nabkade_product_id,
        "torob_product_id": item.torob_product_id,
        "quantity": item.quantity,
        "unit_purchase_price_usd": Decimal(str(item.unit_purchase_price_usd)),
        "total_value_usd": calc.total_value_usd if calc else Decimal("0"),
        "allocated_cost_usd": (calc.allocated_cost_usd if calc else Decimal("0")),
        "allocated_cost_per_unit_usd": (calc.allocated_cost_per_unit_usd if calc else Decimal("0")),
        "landed_cost_usd": (calc.landed_cost_per_unit_usd if calc else Decimal("0")),
        "landed_cost_per_unit_toman": (calc.landed_cost_per_unit_toman if calc else None),
        "market_min_toman": getattr(calc, "market_min_toman", None),
        "market_median_toman": getattr(calc, "market_median_toman", None),
        "margin_vs_min_toman": getattr(calc, "margin_vs_min_toman", None),
        "margin_vs_min_pct": getattr(calc, "margin_vs_min_pct", None),
        "margin_vs_median_toman": getattr(calc, "margin_vs_median_toman", None),
        "margin_vs_median_pct": getattr(calc, "margin_vs_median_pct", None),
        "is_profitable": getattr(calc, "is_profitable", None),
    }


def _ensure_draft(shipment: Shipment):
    if shipment.status == "finalized":
        raise HTTPException(status_code=400, detail="Shipment is finalized and read-only")


@router.post("", response_model=ShipmentDetailOut)
async def create_shipment(payload: ShipmentCreate, session: AsyncSession = Depends(get_session)):
    shipment = Shipment(name=payload.name, notes=payload.notes, status="draft")
    session.add(shipment)
    await session.flush()

    for it in payload.items:
        session.add(ShipmentItem(
            shipment_id=shipment.id,
            nabkade_product_id=it.nabkade_product_id,
            torob_product_id=it.torob_product_id,
            sku=it.sku,
            title=it.title,
            quantity=it.quantity,
            unit_purchase_price_usd=str(it.unit_purchase_price_usd),
        ))
    for c in payload.costs:
        session.add(ShipmentCost(
            shipment_id=shipment.id,
            cost_type=c.cost_type,
            description=c.description,
            amount_usd=str(c.amount_usd),
        ))
    await session.commit()
    await session.refresh(shipment)
    return await _build_detail(session, shipment.id)


@router.get("", response_model=list[ShipmentListRow])
async def list_shipments(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Shipment).order_by(Shipment.id.desc()))
    shipments = result.scalars().all()
    rows = []
    for s in shipments:
        items = await session.execute(
            select(ShipmentItem).where(ShipmentItem.shipment_id == s.id))
        item_list = items.scalars().all()
        total_value = sum((Decimal(str(i.unit_purchase_price_usd)) * i.quantity) for i in item_list)
        costs = await session.execute(
            select(ShipmentCost).where(ShipmentCost.shipment_id == s.id))
        total_costs = sum(Decimal(str(c.amount_usd)) for c in costs.scalars().all())
        rows.append(ShipmentListRow(
            id=s.id, name=s.name, status=s.status,
            created_at=s.created_at, finalized_at=s.finalized_at,
            item_count=len(item_list),
            total_value_usd=total_value,
            total_costs_usd=total_costs,
        ))
    return rows


async def _build_detail(session: AsyncSession, shipment_id: int) -> ShipmentDetailOut:
    shipment = await session.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    items_q = await session.execute(
        select(ShipmentItem).where(ShipmentItem.shipment_id == shipment_id).order_by(ShipmentItem.id))
    items = items_q.scalars().all()
    costs_q = await session.execute(
        select(ShipmentCost).where(ShipmentCost.shipment_id == shipment_id).order_by(ShipmentCost.id))
    costs = costs_q.scalars().all()

    total_value = sum((Decimal(str(i.unit_purchase_price_usd)) * i.quantity) for i in items)
    total_costs = sum(Decimal(str(c.amount_usd)) for c in costs)

    # Always recompute with the CURRENT dollar rate (live margins), for both
    # drafts (preview) and finalized (re-evaluate against today's rate).
    rate = await get_exchange_rate(session)
    skus = [i.sku for i in items if i.sku]
    market = await get_market_prices(session, skus)

    calc_items = [_item_to_calc(i) for i in items]
    calc_costs = [_cost_to_calc(c) for c in costs]
    calc = calculate_shipment(calc_items, calc_costs, rate, market)

    calc_by_id = {c.item_id: c for c in calc.items}
    item_rows = [_calc_to_item_result(i, calc_by_id.get(i.id)) for i in items]
    cost_rows = [ShipmentCostOut(
        id=c.id, cost_type=c.cost_type, description=c.description,
        amount_usd=Decimal(str(c.amount_usd))).model_dump() for c in costs]

    return ShipmentDetailOut(
        id=shipment.id,
        name=shipment.name,
        status=shipment.status,
        notes=shipment.notes,
        dollar_rate=Decimal(str(shipment.dollar_rate)) if shipment.dollar_rate else (Decimal(str(rate)) if rate else None),
        created_at=shipment.created_at,
        finalized_at=shipment.finalized_at,
        total_value_usd=calc.total_value_usd,
        total_costs_usd=calc.total_costs_usd,
        items=[ItemResultOut(**r) for r in item_rows],
        costs=cost_rows,
        message=("finalized" if shipment.status == "finalized" else
                 "not finalized yet — preview computed at current dollar rate"),
    )


@router.get("/{shipment_id}", response_model=ShipmentDetailOut)
async def get_shipment(shipment_id: int, session: AsyncSession = Depends(get_session)):
    return await _build_detail(session, shipment_id)


@router.put("/{shipment_id}", response_model=ShipmentDetailOut)
async def update_shipment(shipment_id: int, payload: ShipmentUpdate, session: AsyncSession = Depends(get_session)):
    shipment = await session.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    _ensure_draft(shipment)

    if payload.name is not None:
        shipment.name = payload.name
    if payload.notes is not None:
        shipment.notes = payload.notes

    if payload.items is not None:
        await session.execute(
            ShipmentItem.__table__.delete().where(ShipmentItem.shipment_id == shipment_id))
        for it in payload.items:
            session.add(ShipmentItem(
                shipment_id=shipment_id,
                nabkade_product_id=it.nabkade_product_id,
                torob_product_id=it.torob_product_id,
                sku=it.sku,
                title=it.title,
                quantity=it.quantity,
                unit_purchase_price_usd=str(it.unit_purchase_price_usd),
            ))
    if payload.costs is not None:
        await session.execute(
            ShipmentCost.__table__.delete().where(ShipmentCost.shipment_id == shipment_id))
        for c in payload.costs:
            session.add(ShipmentCost(
                shipment_id=shipment_id,
                cost_type=c.cost_type,
                description=c.description,
                amount_usd=str(c.amount_usd),
            ))

    await session.commit()
    return await _build_detail(session, shipment_id)


@router.delete("/{shipment_id}")
async def delete_shipment(shipment_id: int, session: AsyncSession = Depends(get_session)):
    shipment = await session.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    _ensure_draft(shipment)
    await session.delete(shipment)
    await session.commit()
    return {"status": "deleted", "id": shipment_id}


@router.post("/{shipment_id}/finalize", response_model=ShipmentDetailOut)
async def finalize_shipment(shipment_id: int, session: AsyncSession = Depends(get_session)):
    shipment = await session.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    _ensure_draft(shipment)

    rate = await get_exchange_rate(session)
    items_q = await session.execute(
        select(ShipmentItem).where(ShipmentItem.shipment_id == shipment_id).order_by(ShipmentItem.id))
    items = items_q.scalars().all()
    costs_q = await session.execute(
        select(ShipmentCost).where(ShipmentCost.shipment_id == shipment_id).order_by(ShipmentCost.id))
    costs = costs_q.scalars().all()

    skus = [i.sku for i in items if i.sku]
    market = await get_market_prices(session, skus)
    calc = calculate_shipment([_item_to_calc(i) for i in items],
                              [_cost_to_calc(c) for c in costs],
                              rate, market)

    # Persist computed per-item allocated/landed costs.
    calc_by_id = {c.item_id: c for c in calc.items}
    for item in items:
        c = calc_by_id.get(item.id)
        if c is not None:
            item.allocated_cost_usd = c.allocated_cost_per_unit_usd
            item.landed_cost_usd = c.landed_cost_per_unit_usd

    from datetime import datetime, timezone
    shipment.status = "finalized"
    shipment.finalized_at = datetime.now(timezone.utc)
    if rate:
        shipment.dollar_rate = str(rate)

    await session.commit()
    return await _build_detail(session, shipment_id)
