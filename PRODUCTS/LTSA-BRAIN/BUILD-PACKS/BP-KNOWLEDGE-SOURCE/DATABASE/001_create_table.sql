CREATE TABLE IF NOT EXISTS public.knowledge_source_registry (
    knowledge_source_id TEXT PRIMARY KEY NOT NULL,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    original_file_name TEXT,
    source_date DATE,
    customer TEXT,
    site TEXT,
    unit TEXT,
    uploaded_by TEXT,
    upload_timestamp TIMESTAMP DEFAULT NOW(),
    source_url TEXT,
    verification_status TEXT NOT NULL DEFAULT 'DRAFT',
    confidence_level NUMERIC,
    file_hash TEXT,
    file_size BIGINT,
    media_type TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT knowledge_source_registry_source_type_check
        CHECK (source_type IN (
            'INSTALLATION_REPORT', 'SERVICE_REPORT', 'INSPECTION_REPORT', 'FAILURE_REPORT',
            'DRAWING', 'DATASHEET', 'BILL_OF_MATERIAL', 'MAINTENANCE_HISTORY',
            'PUMP_MASTER_EXCEL', 'STOCK_EXCEL', 'INSTALLATION_HISTORY_EXCEL',
            'PHOTO', 'VIDEO', 'ENGINEER_NOTE', 'CUSTOMER_NOTE'
        )),
    CONSTRAINT knowledge_source_registry_verification_status_check
        CHECK (verification_status IN ('DRAFT', 'UNDER_REVIEW', 'VERIFIED', 'CANONICAL')),
    CONSTRAINT knowledge_source_registry_file_size_check
        CHECK (file_size IS NULL OR file_size >= 0)
);
