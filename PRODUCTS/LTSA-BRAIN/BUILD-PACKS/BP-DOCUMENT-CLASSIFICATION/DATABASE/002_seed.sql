INSERT INTO public.document_classification (document_classification_id, pdf_document_id, classification_type)
VALUES ('TEST-001', 'TEST-001', 'DATASHEET')
ON CONFLICT (document_classification_id) DO NOTHING;
