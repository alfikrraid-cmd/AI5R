CREATE INDEX IF NOT EXISTS idx_knowledge_source_registry_knowledge_source_id
ON public.knowledge_source_registry (knowledge_source_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_source_registry_source_type
ON public.knowledge_source_registry (source_type);

CREATE INDEX IF NOT EXISTS idx_knowledge_source_registry_verification_status
ON public.knowledge_source_registry (verification_status);
