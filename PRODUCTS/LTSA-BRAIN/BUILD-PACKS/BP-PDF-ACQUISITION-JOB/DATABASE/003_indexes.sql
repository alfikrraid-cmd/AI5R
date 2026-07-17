CREATE INDEX IF NOT EXISTS idx_pdf_acquisition_job_pdf_acquisition_job_id
ON public.pdf_acquisition_job (pdf_acquisition_job_id);

CREATE INDEX IF NOT EXISTS idx_pdf_acquisition_job_knowledge_source_id
ON public.pdf_acquisition_job (knowledge_source_id);

CREATE INDEX IF NOT EXISTS idx_pdf_acquisition_job_pdf_document_id
ON public.pdf_acquisition_job (pdf_document_id);

CREATE INDEX IF NOT EXISTS idx_pdf_acquisition_job_status
ON public.pdf_acquisition_job (status);
