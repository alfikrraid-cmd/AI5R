CREATE INDEX IF NOT EXISTS idx_acquisition_job_acquisition_job_id
ON public.acquisition_job (acquisition_job_id);

CREATE INDEX IF NOT EXISTS idx_acquisition_job_workbook_id
ON public.acquisition_job (workbook_id);

CREATE INDEX IF NOT EXISTS idx_acquisition_job_mapping_profile_id
ON public.acquisition_job (mapping_profile_id);

CREATE INDEX IF NOT EXISTS idx_acquisition_job_status
ON public.acquisition_job (status);
