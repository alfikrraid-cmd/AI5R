-- MWO-LTSA-AUTH-DATA-SCOPE-CLOSURE-001 -- adds the data-scope columns
-- migration 007 explicitly deferred ("visibility is a relationship/scope
-- concern, layered separately -- future MWO-LTSA-AUTH-003 for pump/
-- inventory visibility scope"). This is that layer.
--
-- Additive only, on the existing organization_memberships table -- no
-- new auth engine, no new role. NULL (the default for every existing
-- row and every non-Pertamina role) means "unrestricted" -- SUPERUSER/
-- TAP_ADMIN/TAP_ENGINEER/JOHN_CRANE_ENGINEER are ALWAYS full-access by
-- role rule regardless of these columns (enforced in code,
-- API.auth_service.resolve_area_scope). Only PERTAMINA_ENGINEER/
-- PERTAMINA_VIEWER memberships are ever scope-restricted, and a
-- Pertamina membership with NULL scope is deliberately DENIED (empty
-- scope), never treated as unrestricted -- fail-closed by construction.
--
-- data_scope_type: 'AREA' (single physical Area) or 'MA' (a named
-- supervisor grouping of areas). No DB CHECK constraint enumerating
-- valid data_scope_value strings -- same "fixed vocabulary lives in code,
-- not a duplicated DB list" convention role itself already uses (see
-- migration 007's own comment). Valid values are validated at the
-- application layer only (API.pump_area_scope.AREA_CODES / MA_AREA_GROUPS).
--
-- Only MA2 (HSC + S_PAKNING + HCC) is seeded/supported by application
-- code as of this MWO -- MA1/MA3/MA4's area membership could not be
-- independently corroborated from any authoritative repository source
-- (only a prior session's own supplied business-context dict) and is
-- deliberately left unresolved rather than guessed, per this MWO's own
-- "DO NOT GUESS" instruction. The column itself is generic (any MA
-- value can be stored once resolved); application code intentionally
-- treats an unrecognized MA value as empty scope (deny), never as an
-- error that would need a migration to fix.

ALTER TABLE public.organization_memberships
    ADD COLUMN IF NOT EXISTS data_scope_type VARCHAR(20);

ALTER TABLE public.organization_memberships
    ADD COLUMN IF NOT EXISTS data_scope_value VARCHAR(50);
