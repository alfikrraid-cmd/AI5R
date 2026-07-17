INSERT INTO public.seal_stock (seal_code, quantity_on_hand)
VALUES ('TEST-001', 0)
ON CONFLICT (seal_code) DO NOTHING;
