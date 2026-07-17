CREATE INDEX IF NOT EXISTS idx_media_classification_media_classification_id
ON public.media_classification (media_classification_id);

CREATE INDEX IF NOT EXISTS idx_media_classification_engineering_media_id
ON public.media_classification (engineering_media_id);

CREATE INDEX IF NOT EXISTS idx_media_classification_classification_type
ON public.media_classification (classification_type);
