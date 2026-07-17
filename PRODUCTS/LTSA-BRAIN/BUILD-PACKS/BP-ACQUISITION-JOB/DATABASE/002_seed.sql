INSERT INTO public.acquisition_job (acquisition_job_id, workbook_id, mapping_profile_id)
VALUES ('TEST-001', 'TEST-001', 'TEST-001')
ON CONFLICT (acquisition_job_id) DO NOTHING;
