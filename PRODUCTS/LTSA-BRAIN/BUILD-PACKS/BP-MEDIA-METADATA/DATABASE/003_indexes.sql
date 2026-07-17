CREATE INDEX IF NOT EXISTS idx_media_metadata_media_metadata_id
ON public.media_metadata (media_metadata_id);

CREATE INDEX IF NOT EXISTS idx_media_metadata_engineering_media_id
ON public.media_metadata (engineering_media_id);
