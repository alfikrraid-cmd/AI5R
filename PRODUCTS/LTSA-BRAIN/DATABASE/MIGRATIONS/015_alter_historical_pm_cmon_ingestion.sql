-- MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- closes the schema gaps needed
-- for the historical PM/CMON monthly-report ingestion pipeline, reusing
-- existing architecture end to end (no new generic ingestion engine, per
-- this MWO's own Phase 0 instruction).
--
-- Golden Rule enforced throughout: extracted values are never inserted
-- directly into pm_occurrence/condition_monitoring_reading. They first
-- become document_field_extraction staging rows (the SAME AI-extraction/
-- human-review table MWO-LTSA-INSTALLATION-REPORT-INGESTION-001 already
-- built and this MWO reuses verbatim), reviewed, then promoted through
-- the EXISTING pm_occurrence_repository.create_draft() /
-- condition_monitoring_reading_repository.create_draft() methods -- the
-- same real DRAFT state every other PM/CMON record enters through.
--
-- 1. pdf_document.document_type -- the four historical monthly area
--    reports ("Laporan PM, CM & Pemasangan Seal") are a real, distinct
--    document type; none of the existing eleven values fit ("SERVICE_
--    REPORT"/"INSPECTION_REPORT" would misrepresent a combined PM+CM
--    document as one or the other). One new, precisely-named value.
--
-- 2. document_field_extraction.detected_document_type -- three new
--    values, one per canonical target domain (never a single ambiguous
--    value that would blur the PM/CMON boundary this whole engineering
--    line has repeatedly enforced). Each staged candidate row represents
--    ONE extracted PM occurrence, ONE extracted Condition Monitoring
--    reading, or ONE extracted Finding-sheet row -- a monthly report with
--    hundreds of rows produces hundreds of staging rows, each
--    independently reviewable/rejectable, per Phase 4's "never PDF ->
--    canonical directly" requirement.
--
--    HISTORICAL_FINDING_CANDIDATE exists as its own type, deliberately
--    NOT auto-merged into a HISTORICAL_CMON_READING_CANDIDATE's own
--    `finding` field at extraction time: the real Finding sheet has no
--    per-row reading date, and every real July pump tag has MULTIPLE CM
--    Measuring Report readings within the same monthly report (proven
--    this session: 56/56 HOC tags, 102/102 HCC, 23/23 HSC, 39/39 OM_UTL
--    all have more than one dated reading), so there is no safe,
--    non-fabricated way to auto-pick which specific dated reading a
--    finding's remarks belong to. A human reviewer makes that
--    attachment explicitly (via the existing update_draft(finding=...)
--    path on the CMON repository, once a reading is chosen) -- never
--    guessed by this pipeline.
--
-- 3. pm_occurrence.source_reference / condition_monitoring_reading.
--    source_reference -- the smallest canonical extension necessary
--    (Phase 11's own instruction) to answer "which historical report
--    produced this record" (Phase 16) after promotion, without
--    duplicating the source PDF's bytes into every promoted row (the
--    existing pm_cm_evidence table stores BYTEA evidence; attaching the
--    same multi-page PDF to hundreds of rows would be pure duplication).
--    A free-text pointer, e.g. "document_field_extraction:<id>", the
--    same "informal reference, no DB-level FK, resolved at the
--    application layer" convention pm_schedule.asset_code and this same
--    migration line's own provenance columns already establish. NULL for
--    every normal (non-historical) record -- untouched by this MWO's own
--    real UI workflow.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS is a no-op if already applied; the
-- two CHECK constraints are dropped and re-added with their final
-- definition every run (DDL, not data), safe to re-run.

ALTER TABLE public.pdf_document DROP CONSTRAINT IF EXISTS pdf_document_type_check;
ALTER TABLE public.pdf_document ADD CONSTRAINT pdf_document_type_check
    CHECK (document_type IN (
        'INSTALLATION_REPORT', 'SERVICE_REPORT', 'INSPECTION_REPORT', 'FAILURE_REPORT',
        'JOHN_CRANE_DRAWING', 'DATASHEET', 'MAINTENANCE_MANUAL', 'SERVICE_BULLETIN',
        'ENGINEERING_SPECIFICATION', 'CALIBRATION_REPORT', 'HYDROTEST_REPORT',
        'PM_CMON_MONTHLY_REPORT'
    ));

ALTER TABLE public.document_field_extraction DROP CONSTRAINT IF EXISTS document_field_extraction_detected_type_check;
ALTER TABLE public.document_field_extraction ADD CONSTRAINT document_field_extraction_detected_type_check
    CHECK (detected_document_type IN (
        'MECHANICAL_SEAL_INSTALLATION_REPORT', 'PUMP_DATASHEET',
        'MECHANICAL_SEAL_DRAWING', 'PUMP_DRAWING', 'NAMEPLATE', 'UNKNOWN',
        'HISTORICAL_PM_OCCURRENCE_CANDIDATE', 'HISTORICAL_CMON_READING_CANDIDATE',
        'HISTORICAL_FINDING_CANDIDATE'
    ));

ALTER TABLE public.pm_occurrence
    ADD COLUMN IF NOT EXISTS source_reference TEXT;

ALTER TABLE public.condition_monitoring_reading
    ADD COLUMN IF NOT EXISTS source_reference TEXT;
