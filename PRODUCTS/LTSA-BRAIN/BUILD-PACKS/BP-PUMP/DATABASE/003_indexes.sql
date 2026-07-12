-- DEPRECATED (MWO-P-002 / IR-001): indexes the deprecated `pump_registry` table.
-- See 001_create_table.sql and ../../../DATABASE/CANONICAL_SCHEMA.sql.
CREATE INDEX IF NOT EXISTS idx_pump_registry_pump_code
ON public.pump_registry (pump_code);
