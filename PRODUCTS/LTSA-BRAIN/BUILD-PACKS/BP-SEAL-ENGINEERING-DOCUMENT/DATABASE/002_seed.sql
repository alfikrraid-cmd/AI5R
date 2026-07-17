INSERT INTO public.seal_engineering_document (document_code, seal_code, knowledge_source_id, document_type, title)
VALUES ('TEST-001', 'TEST-001', 'TEST-001', 'DATASHEET', 'Seed Test Document')
ON CONFLICT (document_code) DO NOTHING;
