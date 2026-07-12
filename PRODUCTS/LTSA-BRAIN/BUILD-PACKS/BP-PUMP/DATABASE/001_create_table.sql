-- DEPRECATED (MWO-P-002 / IR-001): duplicate pump entity. The canonical pump
-- table is `ltsa_pumps`, defined in ../../../MODULES/PUMP/DATABASE/001_create_pumps.sql
-- and referenced by the product's real workflows (WF-LTSA-PUMP-REGISTRY-001,
-- WF-LTSA-PUMP-DETAIL-001). See ../../../DATABASE/CANONICAL_SCHEMA.sql.
-- This `pump_registry` table is not queried by any workflow. Kept only for
-- historical reference; do not deploy alongside the canonical schema.
CREATE TABLE IF NOT EXISTS public.pump_registry (
    pump_code TEXT PRIMARY KEY NOT NULL,
    pump_name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    location TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);