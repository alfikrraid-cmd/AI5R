CREATE TABLE IF NOT EXISTS public.seal_stock (
    seal_code TEXT PRIMARY KEY NOT NULL REFERENCES public.seal_registry(seal_code),
    quantity_on_hand NUMERIC NOT NULL DEFAULT 0,
    reorder_point NUMERIC,
    location TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
