CREATE INDEX IF NOT EXISTS idx_document_classification_document_classification_id
ON public.document_classification (document_classification_id);

CREATE INDEX IF NOT EXISTS idx_document_classification_pdf_document_id
ON public.document_classification (pdf_document_id);

CREATE INDEX IF NOT EXISTS idx_document_classification_classification_type
ON public.document_classification (classification_type);
