CREATE TABLE IF NOT EXISTS public.pdf_document (
    pdf_document_id TEXT PRIMARY KEY NOT NULL,
    knowledge_source_id TEXT NOT NULL REFERENCES public.knowledge_source_registry(knowledge_source_id),
    document_name TEXT NOT NULL,
    document_type TEXT NOT NULL,
    file_name TEXT,
    page_count INTEGER,
    file_size BIGINT,
    file_hash TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT pdf_document_type_check
        CHECK (document_type IN (
            'INSTALLATION_REPORT', 'SERVICE_REPORT', 'INSPECTION_REPORT', 'FAILURE_REPORT',
            'JOHN_CRANE_DRAWING', 'DATASHEET', 'MAINTENANCE_MANUAL', 'SERVICE_BULLETIN',
            'ENGINEERING_SPECIFICATION', 'CALIBRATION_REPORT', 'HYDROTEST_REPORT'
        )),
    CONSTRAINT pdf_document_page_count_check CHECK (page_count IS NULL OR page_count >= 0),
    CONSTRAINT pdf_document_file_size_check CHECK (file_size IS NULL OR file_size >= 0)
);
