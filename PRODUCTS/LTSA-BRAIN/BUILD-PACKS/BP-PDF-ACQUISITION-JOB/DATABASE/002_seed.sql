INSERT INTO public.pdf_acquisition_job (pdf_acquisition_job_id, knowledge_source_id, pdf_document_id)
VALUES ('TEST-001', 'TEST-001', 'TEST-001')
ON CONFLICT (pdf_acquisition_job_id) DO NOTHING;
