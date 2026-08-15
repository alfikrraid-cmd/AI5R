-- name / criticality: canonical columns approved by ADR-PUMP-001, added
-- under WO-PUMP-002 (see PRODUCTS/LTSA-BRAIN/MODULES/PUMP/DATABASE/
-- 001_create_pumps.sql and DATABASE/CANONICAL_SCHEMA.sql, both of which
-- already carry these two statements verbatim). This file exists so a
-- production ltsa_pumps table created before WO-PUMP-002 (the pre-existing
-- 14-column shape: id, tag_number, area, location, pump_type, api_plan,
-- seal_type, status, manufacturer, model, drawing_ref, notes, created_at,
-- updated_at -- no name/criticality) can be brought up to the canonical
-- shape without dropping or altering any existing column, row, or
-- constraint. Idempotent: ADD COLUMN IF NOT EXISTS is a no-op on a table
-- that already has these columns, so re-running this file is always safe.
ALTER TABLE ltsa_pumps ADD COLUMN IF NOT EXISTS name VARCHAR(255);
ALTER TABLE ltsa_pumps ADD COLUMN IF NOT EXISTS criticality VARCHAR(50);
