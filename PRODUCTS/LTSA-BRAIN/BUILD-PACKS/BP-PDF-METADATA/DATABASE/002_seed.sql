INSERT INTO public.pdf_metadata (pdf_metadata_id, pdf_document_id)
VALUES ('TEST-001', 'TEST-001')
ON CONFLICT (pdf_metadata_id) DO NOTHING;
