CREATE INDEX IF NOT EXISTS idx_media_acquisition_job_media_acquisition_job_id
ON public.media_acquisition_job (media_acquisition_job_id);

CREATE INDEX IF NOT EXISTS idx_media_acquisition_job_knowledge_source_id
ON public.media_acquisition_job (knowledge_source_id);

CREATE INDEX IF NOT EXISTS idx_media_acquisition_job_engineering_media_id
ON public.media_acquisition_job (engineering_media_id);

CREATE INDEX IF NOT EXISTS idx_media_acquisition_job_status
ON public.media_acquisition_job (status);
