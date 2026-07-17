CREATE INDEX IF NOT EXISTS idx_engineering_media_engineering_media_id
ON public.engineering_media (engineering_media_id);

CREATE INDEX IF NOT EXISTS idx_engineering_media_knowledge_source_id
ON public.engineering_media (knowledge_source_id);

CREATE INDEX IF NOT EXISTS idx_engineering_media_media_type
ON public.engineering_media (media_type);
