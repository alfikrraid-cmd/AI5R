-- DEPRECATED (MWO-P-002 / IR-001): seeds the deprecated `pump_registry` table.
-- See 001_create_table.sql and ../../../DATABASE/CANONICAL_SCHEMA.sql.
INSERT INTO public.pump_registry (pump_code)
VALUES ('TEST-001')
ON CONFLICT (pump_code) DO NOTHING;
