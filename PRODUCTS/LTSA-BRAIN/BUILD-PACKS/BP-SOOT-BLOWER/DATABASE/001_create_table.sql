CREATE TABLE IF NOT EXISTS public.soot_blower_registry (
    soot_blower_code TEXT PRIMARY KEY NOT NULL,
    soot_blower_name TEXT NOT NULL,
    boiler_area TEXT,
    blower_type TEXT,
    manufacturer TEXT,
    model TEXT,
    steam_pressure NUMERIC,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
