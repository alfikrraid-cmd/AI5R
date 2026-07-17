-- Illustrative only, matching every other build pack's 002_seed.sql
-- convention -- not executed by bootstrap_schema.sh or run_verification.sh
-- (see VERIFICATION/bootstrap_schema.sh, which applies CANONICAL_SCHEMA.sql
-- only). Requires two distinct matching seal_registry.seal_code rows to
-- exist for a real apply to succeed.
INSERT INTO public.seal_interchange_compatibility (seal_code, compatible_seal_code)
VALUES ('TEST-001', 'TEST-002')
ON CONFLICT (seal_code, compatible_seal_code) DO NOTHING;
