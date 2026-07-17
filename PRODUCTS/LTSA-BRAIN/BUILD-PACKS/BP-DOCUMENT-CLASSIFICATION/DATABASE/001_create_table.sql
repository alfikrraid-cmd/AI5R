CREATE TABLE IF NOT EXISTS public.document_classification (
    document_classification_id TEXT PRIMARY KEY NOT NULL,
    pdf_document_id TEXT NOT NULL REFERENCES public.pdf_document(pdf_document_id),
    classification_type TEXT NOT NULL,
    classification_version TEXT,
    confidence NUMERIC,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT document_classification_type_check
        CHECK (classification_type IN (
            'INSTALLATION_REPORT', 'SERVICE_REPORT', 'INSPECTION_REPORT', 'FAILURE_REPORT',
            'JOHN_CRANE_DRAWING', 'DATASHEET', 'MAINTENANCE_MANUAL', 'SERVICE_BULLETIN',
            'ENGINEERING_SPECIFICATION', 'CALIBRATION_REPORT', 'HYDROTEST_REPORT'
        ))
);
