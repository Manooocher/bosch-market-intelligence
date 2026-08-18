-- 003_shipments.sql
-- Shipment management + landed-cost module

-- Shipments
CREATE TABLE IF NOT EXISTS shipments (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    dollar_rate NUMERIC,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    finalized_at TIMESTAMPTZ,
    CONSTRAINT chk_shipment_status CHECK (status IN ('draft', 'finalized'))
);

-- Shipment items
CREATE TABLE IF NOT EXISTS shipment_items (
    id SERIAL PRIMARY KEY,
    shipment_id INTEGER NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    nabkade_product_id TEXT,
    torob_product_id TEXT,
    sku TEXT,
    title TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_purchase_price_usd NUMERIC NOT NULL CHECK (unit_purchase_price_usd >= 0),
    allocated_cost_usd NUMERIC DEFAULT 0,
    landed_cost_usd NUMERIC DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Shipment costs
CREATE TABLE IF NOT EXISTS shipment_costs (
    id SERIAL PRIMARY KEY,
    shipment_id INTEGER NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    cost_type TEXT NOT NULL,
    description TEXT,
    amount_usd NUMERIC NOT NULL CHECK (amount_usd >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_cost_type CHECK (cost_type IN (
        'shipping', 'customs', 'insurance', 'warehouse', 'handling', 'other'
    ))
);

CREATE INDEX IF NOT EXISTS idx_shipment_items_shipment ON shipment_items(shipment_id);
CREATE INDEX IF NOT EXISTS idx_shipment_costs_shipment ON shipment_costs(shipment_id);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);