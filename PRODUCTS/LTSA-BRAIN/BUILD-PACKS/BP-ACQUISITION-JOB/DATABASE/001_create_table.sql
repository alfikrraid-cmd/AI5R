CREATE TABLE IF NOT EXISTS public.acquisition_job (
    acquisition_job_id TEXT PRIMARY KEY NOT NULL,
    workbook_id TEXT NOT NULL REFERENCES public.workbook(workbook_id),
    mapping_profile_id TEXT NOT NULL REFERENCES public.mapping_profile(mapping_profile_id),
    status TEXT NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    rows_processed INTEGER,
    rows_valid INTEGER,
    rows_invalid INTEGER,
    error_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT acquisition_job_status_check
        CHECK (status IN ('PENDING', 'IN_PROGRESS', 'READY_FOR_MANUFACTURING', 'FAILED')),
    CONSTRAINT acquisition_job_rows_processed_check CHECK (rows_processed IS NULL OR rows_processed >= 0),
    CONSTRAINT acquisition_job_rows_valid_check CHECK (rows_valid IS NULL OR rows_valid >= 0),
    CONSTRAINT acquisition_job_rows_invalid_check CHECK (rows_invalid IS NULL OR rows_invalid >= 0)
);
