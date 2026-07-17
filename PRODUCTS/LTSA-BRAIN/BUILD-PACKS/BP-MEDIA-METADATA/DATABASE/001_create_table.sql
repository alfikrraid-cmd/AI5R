CREATE TABLE IF NOT EXISTS public.media_metadata (
    media_metadata_id TEXT PRIMARY KEY NOT NULL,
    engineering_media_id TEXT NOT NULL REFERENCES public.engineering_media(engineering_media_id),
    resolution TEXT,
    duration NUMERIC,
    width INTEGER,
    height INTEGER,
    frame_rate NUMERIC,
    audio_channels INTEGER,
    gps_location TEXT,
    camera_device TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT media_metadata_engineering_media_id_unique UNIQUE (engineering_media_id),
    CONSTRAINT media_metadata_width_check CHECK (width IS NULL OR width >= 0),
    CONSTRAINT media_metadata_height_check CHECK (height IS NULL OR height >= 0),
    CONSTRAINT media_metadata_audio_channels_check CHECK (audio_channels IS NULL OR audio_channels >= 0)
);
