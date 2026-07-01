CREATE TABLE IF NOT EXISTS public.pump_registry (
    pump_code TEXT PRIMARY KEY NOT NULL,
    pump_name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    location TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);