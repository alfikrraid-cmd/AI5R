CREATE INDEX IF NOT EXISTS idx_column_mapping_column_mapping_id
ON public.column_mapping (column_mapping_id);

CREATE INDEX IF NOT EXISTS idx_column_mapping_mapping_profile_id
ON public.column_mapping (mapping_profile_id);
