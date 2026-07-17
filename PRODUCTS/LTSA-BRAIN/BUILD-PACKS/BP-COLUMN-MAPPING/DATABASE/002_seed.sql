INSERT INTO public.column_mapping (column_mapping_id, mapping_profile_id, source_column, canonical_attribute)
VALUES ('TEST-001', 'TEST-001', 'TAG NO', 'Pump Tag')
ON CONFLICT (column_mapping_id) DO NOTHING;
