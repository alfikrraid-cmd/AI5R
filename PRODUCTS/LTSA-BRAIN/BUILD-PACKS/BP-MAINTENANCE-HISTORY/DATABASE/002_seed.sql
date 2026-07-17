INSERT INTO public.maintenance_history (maintenance_record_code, action_taken)
VALUES ('TEST-001', 'Seed Test Maintenance Record')
ON CONFLICT (maintenance_record_code) DO NOTHING;
