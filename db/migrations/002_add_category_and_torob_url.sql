-- 002_add_category_and_torob_url.sql
-- Add category column to latest_prices and populate from watch_list
-- Also create migration_log table if it doesn't exist (first manual migration)

-- Create migration tracking table (idempotent)
CREATE TABLE IF NOT EXISTS migration_log (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add category column to latest_prices (idempotent)
ALTER TABLE latest_prices ADD COLUMN IF NOT EXISTS category TEXT;

-- Populate category from watch_list for matched products
UPDATE latest_prices lp
SET category = wl.normalized_category
FROM watch_list wl
WHERE lp.nabkade_product_id = wl.nabkade_product_id
  AND (lp.category IS NULL OR lp.category = '');

-- Log migration
INSERT INTO migration_log (name, applied_at)
VALUES ('002_add_category_and_torob_url', NOW())
ON CONFLICT (name) DO NOTHING;