-- MWO-LTSA-DRAWING-INPUT-R3 -- additive schema-only foundation approved in
-- LTSA_DRAWING_INPUT_R2_CANONICAL_DESIGN (Chief Architect approved
-- Option C). Five new tables. No existing table is altered (except one
-- additive ALTER TABLE ... ADD CONSTRAINT on engineering_drawing itself,
-- a table this same migration creates), no data migrated, no historical
-- backfill, no Type 8B1 insertion -- every table starts empty, including
-- in production, until an authorized later ingestion mission populates
-- it (R5, a separate, later, human-reviewed action).
--
-- engineering_drawing_attribute (R2 Section 9) is explicitly DEFERRED --
-- Chief's own instruction: the ingestion/promotion contract must be
-- proven before introducing generic field-level attribute storage. Not
-- created here.
--
-- seal_engineering_document (the pre-existing, LIVE, seal-scoped
-- document/drawing table Drawing Workspace/Document Workspace already
-- read from today) is NOT touched by this migration at all -- R2's own
-- "Legacy Seal Engineering Document" strategy is phased (retain, then
-- additively cross-reference, then eventually stop reading it for
-- drawings) and no phase of that strategy runs in R3.
--
-- ============================================================
-- engineering_drawing -- logical drawing identity, independent of any
-- one revision/file. drawing_number is nullable and carries NO
-- uniqueness constraint (R2/R3 Chief instruction: different
-- manufacturers may reuse the same number, and unknown/null numbers are
-- legitimate and must coexist) -- never fabricated. No dimensions,
-- materials, BOM, asset_code, seal_code, or raw file bytes live here
-- (R2 Section 3's own explicit exclusion list) -- those stay in
-- seal_registry/internal_component_master (existing authorities) or the
-- new child tables below.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.engineering_drawing (
    drawing_code          TEXT PRIMARY KEY NOT NULL,
    drawing_number        TEXT,
    title                 TEXT NOT NULL,
    manufacturer          TEXT,
    drawing_type          TEXT,
    current_revision_code TEXT,
    created_at            TIMESTAMP DEFAULT NOW(),
    created_by            UUID,
    updated_at            TIMESTAMP DEFAULT NOW(),
    updated_by            UUID
);

CREATE INDEX IF NOT EXISTS idx_engineering_drawing_number
    ON public.engineering_drawing(drawing_number) WHERE drawing_number IS NOT NULL;

-- ============================================================
-- engineering_drawing_revision -- one logical drawing, many revisions.
-- verification_status reuses knowledge_source_registry's own exact
-- vocabulary (DRAFT/UNDER_REVIEW/VERIFIED/CANONICAL), not a new one.
-- revision is nullable -- a source document that does not itself state
-- a revision letter/number must never be assigned a fabricated "Rev 0"
-- (R2's own explicit rule); multiple NULL-revision rows for the same
-- drawing are therefore legitimate and not deduplicated against each
-- other. supersedes_revision_code is a same-table self-FK with an
-- additional composite FK forcing it to belong to the SAME drawing_code
-- (a revision logically can only supersede an earlier revision of its
-- own drawing, never another drawing's) -- this is a strengthening
-- beyond R2's own minimum spec, added because it was cleanly achievable
-- with the same composite-FK technique this migration already needs for
-- current_revision_code below. RESTRICT on both the parent drawing_code
-- FK and the self-referencing supersedes FK: engineering history must
-- never disappear merely because something newer exists (R3 Section 12's
-- own default expectation).
-- ============================================================

CREATE TABLE IF NOT EXISTS public.engineering_drawing_revision (
    revision_code            TEXT PRIMARY KEY NOT NULL,
    drawing_code             TEXT NOT NULL REFERENCES public.engineering_drawing(drawing_code) ON DELETE RESTRICT,
    revision                 TEXT,
    revision_date            DATE,
    verification_status      TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (verification_status IN ('DRAFT', 'UNDER_REVIEW', 'VERIFIED', 'CANONICAL')),
    supersedes_revision_code TEXT REFERENCES public.engineering_drawing_revision(revision_code) ON DELETE RESTRICT,
    notes                    TEXT,
    created_at               TIMESTAMP DEFAULT NOW(),
    created_by               UUID,
    updated_at               TIMESTAMP DEFAULT NOW(),
    updated_by               UUID,
    CONSTRAINT engineering_drawing_revision_drawing_unique UNIQUE (drawing_code, revision_code),
    CONSTRAINT engineering_drawing_revision_no_self_supersede
        CHECK (supersedes_revision_code IS NULL OR supersedes_revision_code <> revision_code),
    CONSTRAINT engineering_drawing_revision_supersedes_same_drawing
        FOREIGN KEY (drawing_code, supersedes_revision_code)
        REFERENCES public.engineering_drawing_revision(drawing_code, revision_code)
);

CREATE INDEX IF NOT EXISTS idx_engineering_drawing_revision_drawing_code
    ON public.engineering_drawing_revision(drawing_code);

-- current_revision_code integrity (R3 Section 5): a plain single-column
-- FK to engineering_drawing_revision.revision_code cannot prove the
-- pointed-to revision belongs to THIS drawing -- a composite FK against
-- the UNIQUE(drawing_code, revision_code) constraint just created above
-- does. Added via ALTER (not inline on the CREATE TABLE above) because
-- engineering_drawing_revision does not exist yet at that point in this
-- file -- the standard, safe way to express a circular two-table
-- reference in Postgres (create both tables, then close the loop).
-- NULL current_revision_code always satisfies a composite FK trivially
-- (Postgres MATCH SIMPLE, the default) -- "no current revision set yet"
-- remains valid at all times. ON DELETE RESTRICT: a revision currently
-- pointed to as "current" cannot be deleted out from under its drawing.
-- DO-block guard (not a plain ALTER) -- Postgres has no
-- ADD CONSTRAINT IF NOT EXISTS; this mirrors migration 035's own exact
-- idempotent-ALTER convention so re-running this file is always safe.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.engineering_drawing'::regclass
          AND conname = 'engineering_drawing_current_revision_fkey'
    ) THEN
        ALTER TABLE public.engineering_drawing
            ADD CONSTRAINT engineering_drawing_current_revision_fkey
            FOREIGN KEY (drawing_code, current_revision_code)
            REFERENCES public.engineering_drawing_revision(drawing_code, revision_code)
            ON DELETE RESTRICT;
    END IF;
END $$;

-- ============================================================
-- engineering_drawing_revision_artifact -- multiple files per revision
-- (R3 Section 6). knowledge_source_id is the ONLY file-identity
-- reference here -- file_hash/file_size/media_type/original_file_name
-- stay exclusively knowledge_source_registry's own authority, never
-- duplicated (R2/R3's own explicit instruction). artifact_class
-- defaults to 'UNKNOWN' (evaluated and required in R2: a freshly
-- acquired file often cannot be classified at acquisition time) and its
-- meaning is immutable once set with intent -- DERIVED_CAD can never
-- become SOURCE_CAD merely because its geometry later proves accurate;
-- a real source file is always a NEW additional artifact row, never an
-- in-place reclassification. derived_from_artifact_code is a nullable
-- self-FK (historical provenance is often incomplete -- not every
-- derived artifact needs a recorded parent) with only a self-reference
-- guard, deliberately NOT constrained to the same revision_code:
-- regenerated artifacts may legitimately trace back to older source
-- material from a prior revision (R3 Section 7's own explicit
-- allowance). RESTRICT on every FK here -- same "never lose history"
-- default as engineering_drawing_revision above.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.engineering_drawing_revision_artifact (
    artifact_code              TEXT PRIMARY KEY NOT NULL,
    revision_code              TEXT NOT NULL REFERENCES public.engineering_drawing_revision(revision_code) ON DELETE RESTRICT,
    knowledge_source_id        TEXT NOT NULL REFERENCES public.knowledge_source_registry(knowledge_source_id) ON DELETE RESTRICT,
    artifact_class             TEXT NOT NULL DEFAULT 'UNKNOWN'
        CHECK (artifact_class IN ('SOURCE_DOCUMENT', 'SOURCE_CAD', 'DERIVED_CAD', 'VIEWER_ASSET', 'UNKNOWN')),
    is_primary                 BOOLEAN NOT NULL DEFAULT FALSE,
    derived_from_artifact_code TEXT REFERENCES public.engineering_drawing_revision_artifact(artifact_code) ON DELETE RESTRICT,
    verification_status        TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (verification_status IN ('DRAFT', 'UNDER_REVIEW', 'VERIFIED', 'CANONICAL')),
    created_at                 TIMESTAMP DEFAULT NOW(),
    created_by                 UUID,
    updated_at                 TIMESTAMP DEFAULT NOW(),
    updated_by                 UUID,
    CONSTRAINT engineering_drawing_revision_artifact_no_self_lineage
        CHECK (derived_from_artifact_code IS NULL OR derived_from_artifact_code <> artifact_code)
);

CREATE INDEX IF NOT EXISTS idx_engineering_drawing_revision_artifact_revision_code
    ON public.engineering_drawing_revision_artifact(revision_code);
CREATE INDEX IF NOT EXISTS idx_engineering_drawing_revision_artifact_knowledge_source_id
    ON public.engineering_drawing_revision_artifact(knowledge_source_id);

-- At most one active primary artifact per (revision, artifact_class) --
-- R3 Section 8's own recommendation: a revision may have one primary PDF
-- AND, independently, one primary STEP AND one primary GLB all at once
-- (never one single global primary forced across every class).
CREATE UNIQUE INDEX IF NOT EXISTS idx_engineering_drawing_revision_artifact_one_primary
    ON public.engineering_drawing_revision_artifact(revision_code, artifact_class)
    WHERE is_primary;

-- ============================================================
-- engineering_drawing_link -- polymorphic ASSET/SEAL/COMPONENT link,
-- reusing the exact informal-polymorphic-reference convention already
-- proven by pm_cm_evidence.record_code / ltsa_finding.source_record_code
-- (no DB FK on target_code -- application-layer validation is R4's job,
-- per this migration's own Section 16 change boundary). relationship_type
-- is the minimum, evidence-backed vocabulary from R2 (APPLIES_TO/
-- DEPICTS/COMPONENT_OF only -- COMPATIBLE_WITH deliberately excluded so
-- this table never competes with the already-real seal_pump_compatibility
-- table; ASSEMBLY_OF deliberately excluded as redundant with
-- DEPICTS+target_type=COMPONENT against an internal_component_master row
-- whose component_class='MECHANICAL_SEAL_ASSY'). retracted_at/
-- retracted_by let an incorrect link be excluded from "currently
-- applicable" queries WITHOUT deleting the row -- provenance history is
-- never destroyed merely because a link was later proven wrong.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.engineering_drawing_link (
    link_code           TEXT PRIMARY KEY NOT NULL,
    drawing_code        TEXT NOT NULL REFERENCES public.engineering_drawing(drawing_code) ON DELETE RESTRICT,
    target_type         TEXT NOT NULL CHECK (target_type IN ('ASSET', 'SEAL', 'COMPONENT')),
    target_code         TEXT NOT NULL,
    relationship_type   TEXT NOT NULL CHECK (relationship_type IN ('APPLIES_TO', 'DEPICTS', 'COMPONENT_OF')),
    verification_status TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (verification_status IN ('DRAFT', 'UNDER_REVIEW', 'VERIFIED', 'CANONICAL')),
    source_reference    TEXT,
    retracted_at        TIMESTAMP,
    retracted_by        UUID,
    created_at          TIMESTAMP DEFAULT NOW(),
    created_by          UUID,
    updated_at          TIMESTAMP DEFAULT NOW(),
    updated_by          UUID
);

CREATE INDEX IF NOT EXISTS idx_engineering_drawing_link_target
    ON public.engineering_drawing_link(target_type, target_code);

-- Prevents a literal duplicate ACTIVE link (same drawing/target/
-- relationship) while allowing the exact same tuple to be re-established
-- later as a brand-new row after the earlier one was retracted -- the
-- partial index only counts rows where retracted_at IS NULL, so a
-- retracted row no longer blocks a fresh one (R3 Section 10's own
-- explicit requirement).
CREATE UNIQUE INDEX IF NOT EXISTS idx_engineering_drawing_link_active_unique
    ON public.engineering_drawing_link(drawing_code, target_type, target_code, relationship_type)
    WHERE retracted_at IS NULL;

-- ============================================================
-- engineering_drawing_bom_line -- the drawing's own ENGINEERING
-- DEFINITION bill of material, FK'd to revision_code (not drawing_code)
-- because BOM composition is a revision-level fact (a later revision may
-- swap a component the earlier one used). component_id is nullable --
-- an as-drawn line naming a component not yet in internal_component_
-- master is a legitimate, common state, never blocked on catalog
-- completeness -- component_description preserves the as-printed text
-- verbatim regardless of whether component_id is later resolved.
-- Completely independent of installation_report.bill_of_material (that
-- JSONB column is TRANSACTION EVIDENCE -- what was actually observed on
-- one visit -- and is never read, written, or overwritten by this
-- migration or table).
-- ============================================================

CREATE TABLE IF NOT EXISTS public.engineering_drawing_bom_line (
    bom_line_code             TEXT PRIMARY KEY NOT NULL,
    revision_code             TEXT NOT NULL REFERENCES public.engineering_drawing_revision(revision_code) ON DELETE RESTRICT,
    item_position             TEXT,
    component_id              TEXT REFERENCES public.internal_component_master(component_id) ON DELETE RESTRICT,
    component_description     TEXT,
    quantity                  NUMERIC,
    material_or_specification TEXT,
    notes                     TEXT,
    created_at                TIMESTAMP DEFAULT NOW(),
    created_by                UUID,
    updated_at                TIMESTAMP DEFAULT NOW(),
    updated_by                UUID
);

CREATE INDEX IF NOT EXISTS idx_engineering_drawing_bom_line_revision_code
    ON public.engineering_drawing_bom_line(revision_code);
CREATE INDEX IF NOT EXISTS idx_engineering_drawing_bom_line_component_id
    ON public.engineering_drawing_bom_line(component_id) WHERE component_id IS NOT NULL;

-- Rollback (manual, not executed by this file -- forward-only migration
-- convention already established in this directory, see migrations
-- 035/036/037):
--
--   ALTER TABLE public.engineering_drawing DROP CONSTRAINT IF EXISTS engineering_drawing_current_revision_fkey;
--   DROP TABLE IF EXISTS public.engineering_drawing_bom_line;
--   DROP TABLE IF EXISTS public.engineering_drawing_link;
--   DROP TABLE IF EXISTS public.engineering_drawing_revision_artifact;
--   DROP TABLE IF EXISTS public.engineering_drawing_revision;
--   DROP TABLE IF EXISTS public.engineering_drawing;
--
-- Safe unconditionally: all five tables are new, nothing else references
-- them yet, and this migration performs no data changes to roll back.
-- The current_revision_code FK must be dropped first (drop order above)
-- since engineering_drawing_revision cannot be dropped while it is
-- referenced.
