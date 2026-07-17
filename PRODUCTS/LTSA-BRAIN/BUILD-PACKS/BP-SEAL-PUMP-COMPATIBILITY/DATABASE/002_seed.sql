-- Illustrative only, matching every other build pack's 002_seed.sql
-- convention -- not executed by bootstrap_schema.sh or run_verification.sh
-- (see VERIFICATION/bootstrap_schema.sh, which applies CANONICAL_SCHEMA.sql
-- only). Requires matching seal_registry.seal_code and
-- ltsa_pumps.tag_number rows to exist for a real apply to succeed.
INSERT INTO public.seal_pump_compatibility (seal_code, pump_tag_number)
VALUES ('TEST-001', 'TEST-PUMP-001')
ON CONFLICT (seal_code, pump_tag_number) DO NOTHING;
