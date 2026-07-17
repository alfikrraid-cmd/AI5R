CREATE TABLE IF NOT EXISTS public.media_classification (
    media_classification_id TEXT PRIMARY KEY NOT NULL,
    engineering_media_id TEXT NOT NULL REFERENCES public.engineering_media(engineering_media_id),
    classification_type TEXT NOT NULL,
    classification_version TEXT,
    confidence NUMERIC,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT media_classification_type_check
        CHECK (classification_type IN (
            'PHOTO', 'VIDEO', 'AUDIO', 'THERMAL_IMAGE', 'INFRARED_IMAGE',
            'INSPECTION_IMAGE', 'CCTV_RECORDING', 'DRONE_RECORDING', 'OTHER'
        ))
);
