INSERT INTO public.media_acquisition_job (media_acquisition_job_id, knowledge_source_id, engineering_media_id)
VALUES ('TEST-001', 'TEST-001', 'TEST-001')
ON CONFLICT (media_acquisition_job_id) DO NOTHING;
