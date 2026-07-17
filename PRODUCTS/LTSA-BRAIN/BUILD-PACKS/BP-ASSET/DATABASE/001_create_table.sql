CREATE TABLE IF NOT EXISTS public.asset_registry (
    asset_code TEXT PRIMARY KEY NOT NULL,
    asset_name TEXT NOT NULL,
    asset_type TEXT,
    area TEXT,
    manufacturer TEXT,
    model TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
