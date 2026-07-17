INSERT INTO public.pdf_document (pdf_document_id, knowledge_source_id, document_name, document_type)
VALUES ('TEST-001', 'TEST-001', 'Seed Test PDF Document', 'DATASHEET')
ON CONFLICT (pdf_document_id) DO NOTHING;
