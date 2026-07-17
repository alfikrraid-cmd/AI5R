-- work_order.asset_code / asset_type is an intentional, documented polymorphic
-- reference (not a foreign key): an asset may live in pump_registry, seal_registry,
-- asset_registry, or soot_blower_registry -- four separate tables with no common
-- supertype in this schema. Enforcing a real FK would require introducing a new
-- supertype table, which is new architecture and out of MO-001's scope (see
-- MANUFACTURING/MO-001/MO-001-SPECIFICATION.md, section 2). asset_type records
-- which registry asset_code belongs to, resolved at the application/workflow layer.
CREATE TABLE IF NOT EXISTS public.work_order (
    work_order_code TEXT PRIMARY KEY NOT NULL,
    customer_code TEXT,
    asset_code TEXT,
    asset_type TEXT,
    description TEXT NOT NULL,
    priority TEXT DEFAULT 'NORMAL',
    status TEXT DEFAULT 'OPEN',
    assigned_to TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP
);
