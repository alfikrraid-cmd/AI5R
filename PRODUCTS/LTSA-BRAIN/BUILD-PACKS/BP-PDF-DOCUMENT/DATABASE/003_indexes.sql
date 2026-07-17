CREATE INDEX IF NOT EXISTS idx_pdf_document_pdf_document_id
ON public.pdf_document (pdf_document_id);

CREATE INDEX IF NOT EXISTS idx_pdf_document_knowledge_source_id
ON public.pdf_document (knowledge_source_id);

CREATE INDEX IF NOT EXISTS idx_pdf_document_document_type
ON public.pdf_document (document_type);
