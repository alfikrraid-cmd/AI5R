-- MWO-025J2-WHATSAPP-CONFIRMATION-SCOPE-HARDENING -- binds each pending
-- intake to the organization it was created under, so confirmation can
-- verify the confirming identity's currently-resolved org still matches
-- instead of silently trusting whichever membership identity resolution
-- happens to pick for a multi-org user; and records the provider_message_id
-- of AI5R's own most recent outbound reply for a pending row, so a later
-- inbound reply's Meta context.id can be resolved to the exact pending
-- conversation it belongs to instead of always falling back to "most
-- recent actionable row." Both columns are nullable and purely additive --
-- no existing row, query, or constraint is affected; only
-- whatsapp_intake_pending is touched. NOT applied to production by this
-- MWO -- report only, per instruction.

ALTER TABLE public.whatsapp_intake_pending
    ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES public.organizations(id),
    ADD COLUMN IF NOT EXISTS last_outbound_provider_message_id TEXT;

CREATE INDEX IF NOT EXISTS idx_whatsapp_intake_outbound_message
    ON public.whatsapp_intake_pending(last_outbound_provider_message_id);
