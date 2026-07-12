-- DEPRECATED (MWO-P-002 / IR-001): rollback for the deprecated `pump_registry` table.
-- See 001_create_table.sql and ../../../DATABASE/CANONICAL_SCHEMA.sql.
DROP TABLE IF EXISTS public.pump_registry;
