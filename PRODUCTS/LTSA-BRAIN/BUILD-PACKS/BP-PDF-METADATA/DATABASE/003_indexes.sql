CREATE INDEX IF NOT EXISTS idx_pdf_metadata_pdf_metadata_id
ON public.pdf_metadata (pdf_metadata_id);

CREATE INDEX IF NOT EXISTS idx_pdf_metadata_pdf_document_id
ON public.pdf_metadata (pdf_document_id);
