CREATE TABLE IF NOT EXISTS public.media_acquisition_job (
    media_acquisition_job_id TEXT PRIMARY KEY NOT NULL,
    knowledge_source_id TEXT NOT NULL REFERENCES public.knowledge_source_registry(knowledge_source_id),
    engineering_media_id TEXT NOT NULL REFERENCES public.engineering_media(engineering_media_id),
    status TEXT NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP,
    validation_errors TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT media_acquisition_job_status_check
        CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'))
);
