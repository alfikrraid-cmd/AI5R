CREATE TABLE IF NOT EXISTS public.seal_pump_compatibility (
    seal_code TEXT NOT NULL REFERENCES public.seal_registry(seal_code),
    pump_tag_number VARCHAR(100) NOT NULL REFERENCES public.ltsa_pumps(tag_number),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (seal_code, pump_tag_number)
);
