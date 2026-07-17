CREATE INDEX IF NOT EXISTS idx_document_field_extraction_source
    ON public.document_field_extraction(source_document_id, source_document_type);

CREATE INDEX IF NOT EXISTS idx_document_field_extraction_status
    ON public.document_field_extraction(status);

CREATE INDEX IF NOT EXISTS idx_document_field_extraction_pump_tag_number
    ON public.document_field_extraction(pump_tag_number);

CREATE INDEX IF NOT EXISTS idx_document_field_extraction_seal_code
    ON public.document_field_extraction(seal_code);
