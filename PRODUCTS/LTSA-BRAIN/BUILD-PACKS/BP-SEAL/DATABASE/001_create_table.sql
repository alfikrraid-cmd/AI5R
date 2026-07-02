CREATE TABLE IF NOT EXISTS public.seal_registry (
    seal_code TEXT PRIMARY KEY NOT NULL,
    seal_name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    shaft_size NUMERIC,
    material TEXT,
    temperature_limit NUMERIC,
    pressure_limit NUMERIC,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);