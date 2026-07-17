CREATE TABLE IF NOT EXISTS public.engineering_media (
    engineering_media_id TEXT PRIMARY KEY NOT NULL,
    knowledge_source_id TEXT NOT NULL REFERENCES public.knowledge_source_registry(knowledge_source_id),
    media_name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    file_name TEXT,
    file_size BIGINT,
    file_hash TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT engineering_media_type_check
        CHECK (media_type IN (
            'PHOTO', 'VIDEO', 'AUDIO', 'THERMAL_IMAGE', 'INFRARED_IMAGE',
            'INSPECTION_IMAGE', 'CCTV_RECORDING', 'DRONE_RECORDING', 'OTHER'
        )),
    CONSTRAINT engineering_media_file_size_check CHECK (file_size IS NULL OR file_size >= 0)
);
