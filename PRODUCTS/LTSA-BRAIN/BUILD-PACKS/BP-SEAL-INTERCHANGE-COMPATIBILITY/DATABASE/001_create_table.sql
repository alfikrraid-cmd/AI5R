CREATE TABLE IF NOT EXISTS public.seal_interchange_compatibility (
    seal_code TEXT NOT NULL REFERENCES public.seal_registry(seal_code),
    compatible_seal_code TEXT NOT NULL REFERENCES public.seal_registry(seal_code),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (seal_code, compatible_seal_code),
    CONSTRAINT seal_interchange_not_self CHECK (seal_code <> compatible_seal_code)
);
