CREATE INDEX IF NOT EXISTS idx_seal_pump_compatibility_seal_code
ON public.seal_pump_compatibility (seal_code);

CREATE INDEX IF NOT EXISTS idx_seal_pump_compatibility_pump_tag_number
ON public.seal_pump_compatibility (pump_tag_number);
