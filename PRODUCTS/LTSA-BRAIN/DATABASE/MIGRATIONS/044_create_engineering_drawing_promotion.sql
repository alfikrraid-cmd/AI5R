-- MWO-LTSA-DRAWING-INPUT-R5D.0A -- additive promotion provenance/idempotency
-- authority approved in DRAWING_R5D0_ATOMIC_PROMOTION_DESIGN Section 3. One
-- new table only. Migrations 038/039 are NOT altered.
--
-- SCOPE NOTE / R5D.0A1 UPDATE: R5D0's own design also proposed two
-- expression/partial UNIQUE indexes for drawing/revision identity
-- (engineering_drawing(upper(btrim(manufacturer)), drawing_number) and
-- engineering_drawing_revision(drawing_code, revision)). R5D.0A originally
-- deferred both, pending a live duplicate-data audit that this session's
-- permission policy blocked at the time. That audit was completed under
-- explicit, scoped Chief authorization (R5D.0A1, read-only, three exact
-- queries, BEGIN READ ONLY / ROLLBACK, against ai5r-runtime-postgres-1's
-- own ltsa_brain database): engineering_drawing and
-- engineering_drawing_revision do not exist yet in that live database at
-- all (migrations 038/039/040 have never been applied there -- every
-- Drawing-R3 through R5D.0A migration/table has so far existed only in
-- this session's own disposable, ephemeral test-Postgres containers).
-- Zero rows therefore trivially means zero possible duplicate groups --
-- stronger than a COUNT()=0 on an existing table, since duplication is
-- structurally impossible in a table that has not been created. Both
-- indexes are added below as part of this same table-creation migration
-- (not a separate follow-up file) since they were never applied anywhere
-- and therefore carry no risk of colliding with existing rows when this
-- migration eventually runs for the first time against any real
-- environment, including the live one audited here.
--
-- engineering_drawing_promotion is an audit/idempotency SPINE, not a
-- replacement for engineering_drawing/_revision/_revision_artifact/
-- _attribute/_bom_line/_link -- it records which single reviewed staging
-- candidate (document_field_extraction) produced or reused which primary
-- canonical drawing/revision/artifact context. UNIQUE(candidate_id) is the
-- DB-enforced "at most one promotion per candidate" guarantee R5D's future
-- atomic transaction will rely on (inserted in that same future
-- transaction, alongside the candidate's REVIEWED -> SAVED transition --
-- no row is inserted by this migration itself).
--
-- Column-type/name adjustments from the mission's own literal spec, made
-- per its own "adjust only if required by existing schema convention"
-- allowance, and disclosed here rather than silently deviating:
--   * promoted_by is UUID (not TEXT) -- matches created_by/updated_by/
--     reviewed_by across every other table in this migration family
--     (migrations 007/038/039 all use UUID for actor columns).
--   * promoted_at/created_at are TIMESTAMP (not TIMESTAMPTZ) -- matches
--     migrations 038/039's own created_at/updated_at/revision_date
--     convention exactly (this schema has never used TIMESTAMPTZ anywhere).
--   * No updated_at/updated_by -- this row is insert-only/immutable once
--     written (a promotion is never edited in place; a corrected
--     classification or a superseding revision is always a NEW canonical
--     row elsewhere, never a rewrite of this audit spine), so there is
--     nothing to timestamp a second time.
--
-- FK consistency (Section 8): drawing_code/revision_code/artifact_code are
-- NOT independently-verified foreign keys that could point a revision at
-- an unrelated drawing or an artifact at an unrelated revision -- this
-- migration reuses the EXACT composite-FK technique migrations 038/039
-- already proved for current_revision_code and
-- engineering_drawing_attribute.source_artifact_code: (drawing_code,
-- revision_code) is FK'd against engineering_drawing_revision's own
-- existing UNIQUE(drawing_code, revision_code), and (revision_code,
-- artifact_code) is FK'd against engineering_drawing_revision_artifact's
-- own existing UNIQUE(revision_code, artifact_code) (added in migration
-- 039). Both composite FKs can be declared inline here (unlike 038's own
-- current_revision_code, which needed a later ALTER/DO-block only because
-- of its circular same-migration self-reference) since both target unique
-- constraints already exist in the database by the time this migration
-- runs. RESTRICT on every FK (candidate_id included) -- same "never lose
-- history, never CASCADE" default this entire migration family already
-- uses; a promoted candidate's own document_field_extraction row can never
-- be deleted out from under its promotion record.
--
-- candidate_id has NO composite-FK entanglement with drawing/revision/
-- artifact (document_field_extraction carries no drawing/revision/artifact
-- foreign keys of its own to compose against) -- its own plain FK plus the
-- UNIQUE(candidate_id) constraint below is the full identity guarantee this
-- table needs for that column.

CREATE TABLE IF NOT EXISTS public.engineering_drawing_promotion (
    promotion_code TEXT PRIMARY KEY NOT NULL,
    candidate_id   TEXT NOT NULL REFERENCES public.document_field_extraction(document_field_extraction_id) ON DELETE RESTRICT,
    drawing_code   TEXT NOT NULL REFERENCES public.engineering_drawing(drawing_code) ON DELETE RESTRICT,
    revision_code  TEXT NOT NULL REFERENCES public.engineering_drawing_revision(revision_code) ON DELETE RESTRICT,
    artifact_code  TEXT NOT NULL REFERENCES public.engineering_drawing_revision_artifact(artifact_code) ON DELETE RESTRICT,
    promoted_by    UUID NOT NULL,
    promoted_at    TIMESTAMP NOT NULL,
    created_at     TIMESTAMP DEFAULT NOW(),
    CONSTRAINT engineering_drawing_promotion_candidate_unique UNIQUE (candidate_id),
    CONSTRAINT engineering_drawing_promotion_revision_same_drawing
        FOREIGN KEY (drawing_code, revision_code)
        REFERENCES public.engineering_drawing_revision(drawing_code, revision_code)
        ON DELETE RESTRICT,
    CONSTRAINT engineering_drawing_promotion_artifact_same_revision
        FOREIGN KEY (revision_code, artifact_code)
        REFERENCES public.engineering_drawing_revision_artifact(revision_code, artifact_code)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_engineering_drawing_promotion_drawing_code
    ON public.engineering_drawing_promotion(drawing_code);
CREATE INDEX IF NOT EXISTS idx_engineering_drawing_promotion_revision_code
    ON public.engineering_drawing_promotion(revision_code);
CREATE INDEX IF NOT EXISTS idx_engineering_drawing_promotion_artifact_code
    ON public.engineering_drawing_promotion(artifact_code);

-- ============================================================
-- Drawing identity uniqueness (R5D0 Section 4 / R5D.0A1 Section 9).
-- manufacturer is matched trim+case-insensitively (upper(btrim(...))) --
-- "John Crane" / " John Crane " / "JOHN CRANE" all collide -- but
-- "JOHNCRANE" (no space) does NOT collide with "JOHN CRANE" (no
-- whitespace-collapsing, no fuzzy/alias matching, per R5D0's own
-- conservative MANUFACTURER_MATCH_MODEL). drawing_number stays
-- exact/case-preserved -- it is NOT wrapped in upper()/btrim() here.
-- The stored manufacturer/drawing_number VALUES are never normalized or
-- rewritten by this index -- only the uniqueness CHECK is normalized.
-- Partial (WHERE both NOT NULL): a NULL manufacturer or NULL
-- drawing_number is not a comparable identity per R5D0's own
-- DRAWING_NUMBER_NULL_MODEL (each such candidate legitimately becomes its
-- own NEW_DRAWING; this index must never block that).
-- ============================================================

CREATE UNIQUE INDEX IF NOT EXISTS idx_engineering_drawing_identity_unique
    ON public.engineering_drawing (
        upper(btrim(manufacturer)),
        drawing_number
    )
    WHERE manufacturer IS NOT NULL
      AND drawing_number IS NOT NULL;

-- ============================================================
-- Revision identity uniqueness (R5D0 Section 5 / R5D.0A1 Section 10).
-- revision is compared exactly (no case-folding/trim -- R5D0 never
-- proposed normalizing revision letters/numbers, only manufacturer).
-- Partial (WHERE revision IS NOT NULL): NULL revisions remain
-- intentionally repeatable -- each unknown-revision candidate may
-- legitimately produce its own distinct revision row under the same
-- drawing (R5D0's own REVISION_NULL_MODEL), never deduplicated against
-- each other.
-- ============================================================

CREATE UNIQUE INDEX IF NOT EXISTS idx_engineering_drawing_revision_identity_unique
    ON public.engineering_drawing_revision (drawing_code, revision)
    WHERE revision IS NOT NULL;

-- Rollback (manual, not executed by this file -- forward-only migration
-- convention already established in this directory):
--
--   DROP INDEX IF EXISTS public.idx_engineering_drawing_revision_identity_unique;
--   DROP INDEX IF EXISTS public.idx_engineering_drawing_identity_unique;
--   DROP TABLE IF EXISTS public.engineering_drawing_promotion;
--
-- Safe unconditionally: the table is new and the two indexes were verified
-- (R5D.0A1, live read-only audit) to have zero pre-existing rows to
-- conflict with in every environment checked -- this migration performs
-- no data changes to roll back.
