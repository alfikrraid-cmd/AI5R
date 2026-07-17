CREATE TABLE IF NOT EXISTS public.workbook (
    workbook_id TEXT PRIMARY KEY NOT NULL,
    knowledge_source_id TEXT NOT NULL REFERENCES public.knowledge_source_registry(knowledge_source_id),
    workbook_type TEXT NOT NULL,
    workbook_name TEXT NOT NULL,
    workbook_version TEXT,
    sheet_count INTEGER,
    created_date DATE,
    imported_date DATE,
    uploaded_by TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT workbook_type_check
        CHECK (workbook_type IN (
            'PUMP_MASTER', 'MECHANICAL_SEAL_MASTER', 'SEAL_STOCK', 'SEAL_INTERCHANGE',
            'PUMP_COMPATIBILITY', 'INSTALLATION_HISTORY', 'MAINTENANCE_HISTORY',
            'ENGINEER_MASTER', 'CUSTOMER_MASTER', 'VENDOR_MASTER', 'BILL_OF_MATERIAL'
        )),
    CONSTRAINT workbook_sheet_count_check CHECK (sheet_count IS NULL OR sheet_count >= 0)
);
