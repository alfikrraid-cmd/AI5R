CREATE INDEX IF NOT EXISTS idx_mapping_profile_mapping_profile_id
ON public.mapping_profile (mapping_profile_id);

CREATE INDEX IF NOT EXISTS idx_mapping_profile_workbook_type
ON public.mapping_profile (workbook_type);
