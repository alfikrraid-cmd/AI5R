-- MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001
--
-- Additive only. KIMAP Pertamina and GPN John Crane are business
-- identifiers hanging off canonical seal identity, never part of that
-- identity itself (Hard Rule 2). Phase 2 cardinality decision, from real
-- evidence:
--   - seal_registry (not seal_stock) is the identifier master: it is the
--     one-row-per-distinct-seal table (61 rows, matches seal_registry's
--     own row count); seal_stock has only 24 rows and is not present for
--     every seal, so it cannot be an identity-adjacent master.
--   - Modeled as simple nullable columns (1 KIMAP, 1 GPN per seal), not a
--     relation table: no real data anywhere (golden workbook, ingestion
--     code, CANONICAL_SCHEMA.sql) establishes one-to-many/many-to-many
--     cardinality for either identifier (Phase 1 audit found zero KIMAP
--     occurrences and zero seal-level GPN occurrences in the approved
--     source workbook's Mechseal/Gudang/HSC & SPK sheets). A relation
--     table with no evidenced multiplicity would be exactly the
--     "generalized identifier engine without evidence" Hard Rule 2
--     forbids; a future migration can introduce one if real KIMAP/GPN
--     data ever proves multiplicity is needed.
--
-- gpn_john_crane is deliberately NOT named gpn_number: that name already
-- means something different on internal_component_master (a per-O-Ring
-- "Our Part No" component reference, confirmed via
-- ltsa_internal_component_ingestion.py's _project_o_ring_rows column-7
-- mapping) -- a component-level identifier, not a seal-assembly-level
-- one. Using a distinct column name on a distinct table reinforces Hard
-- Rule 5 (component GPN and seal GPN are never the same identifier) at
-- the schema level, not only in application code.
--
-- created_by/updated_by follow the migration-012 attribution pattern
-- (nullable, conceptually referencing users.id) -- but as a PLAIN UUID
-- with NO DB-level FK, because seal_registry is defined far earlier than
-- `users` in CANONICAL_SCHEMA.sql's own bootstrap order (`users` is not
-- even present in that file at all -- only migration 007 creates it).
-- Identical reasoning already applied once to
-- document_field_extraction.reviewed_by
-- (010_alter_document_field_extraction_review_provenance.sql).
--
-- Nullable, no defaults, no fabricated values -- every existing row
-- (all 61 seal_registry rows from the production import) keeps working
-- unchanged with all four new columns NULL. ltsa_pump_inventory_db_upsert
-- .py's own seal_registry INSERT/UPDATE never references these columns
-- (its fixed 4-key payload is seal_code/seal_name/shaft_size/
-- manufacturer only), so ingestion is unaffected without any code change.
ALTER TABLE public.seal_registry
    ADD COLUMN IF NOT EXISTS kimap_pertamina TEXT,
    ADD COLUMN IF NOT EXISTS gpn_john_crane TEXT,
    ADD COLUMN IF NOT EXISTS created_by UUID,
    ADD COLUMN IF NOT EXISTS updated_by UUID;
