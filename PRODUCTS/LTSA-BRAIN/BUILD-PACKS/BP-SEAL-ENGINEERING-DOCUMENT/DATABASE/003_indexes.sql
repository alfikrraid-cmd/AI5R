CREATE INDEX IF NOT EXISTS idx_seal_engineering_document_document_code
ON public.seal_engineering_document (document_code);

CREATE INDEX IF NOT EXISTS idx_seal_engineering_document_seal_code
ON public.seal_engineering_document (seal_code);

CREATE INDEX IF NOT EXISTS idx_seal_engineering_document_document_type
ON public.seal_engineering_document (document_type);

CREATE INDEX IF NOT EXISTS idx_seal_engineering_document_knowledge_source_id
ON public.seal_engineering_document (knowledge_source_id);
