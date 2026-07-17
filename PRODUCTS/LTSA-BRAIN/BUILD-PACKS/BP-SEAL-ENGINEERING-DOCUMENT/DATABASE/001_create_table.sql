CREATE TABLE IF NOT EXISTS public.seal_engineering_document (
    document_code TEXT PRIMARY KEY NOT NULL,
    seal_code TEXT NOT NULL REFERENCES public.seal_registry(seal_code),
    knowledge_source_id TEXT REFERENCES public.knowledge_source_registry(knowledge_source_id),
    document_type TEXT NOT NULL,
    document_number TEXT,
    title TEXT NOT NULL,
    revision TEXT,
    issue_date DATE,
    manufacturer TEXT,
    language TEXT,
    description TEXT,
    file_reference TEXT,
    file_name TEXT,
    file_format TEXT,
    page_count INTEGER,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT seal_engineering_document_type_check
        CHECK (document_type IN (
            'DRAWING', 'DATASHEET', 'INSTALLATION_GUIDE', 'INSPECTION_SHEET',
            'MAINTENANCE_MANUAL', 'SERVICE_BULLETIN', 'ENGINEERING_SPECIFICATION'
        )),
    CONSTRAINT seal_engineering_document_page_count_check
        CHECK (page_count IS NULL OR page_count >= 0)
);
