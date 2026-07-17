CREATE TABLE IF NOT EXISTS public.column_mapping (
    column_mapping_id TEXT PRIMARY KEY NOT NULL,
    mapping_profile_id TEXT NOT NULL REFERENCES public.mapping_profile(mapping_profile_id),
    source_column TEXT NOT NULL,
    canonical_attribute TEXT NOT NULL,
    is_mandatory BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
