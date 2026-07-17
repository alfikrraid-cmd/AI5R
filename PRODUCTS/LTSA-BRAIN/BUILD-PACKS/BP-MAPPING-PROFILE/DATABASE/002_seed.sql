INSERT INTO public.mapping_profile (mapping_profile_id, profile_name, workbook_type)
VALUES ('TEST-001', 'Seed Test Mapping Profile', 'PUMP_MASTER')
ON CONFLICT (mapping_profile_id) DO NOTHING;
