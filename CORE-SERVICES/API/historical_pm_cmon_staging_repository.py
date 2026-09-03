"""MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- staging repository for
historical PM/Condition Monitoring candidates extracted from monthly
"Laporan PM, CM & Pemasangan Seal" reports.

Reuses document_field_extraction verbatim (the SAME AI-extraction/human-
review staging table MWO-LTSA-INSTALLATION-REPORT-INGESTION-001 already
built and installation_review_service.py already governs) rather than a
second staging table -- per this MWO's own "Do NOT build a second generic
ingestion engine" instruction. Three new detected_document_type values
(migration 015) keep the PM/CMON/Finding domains distinct at the staging
layer too, mirroring the same separation pm_occurrence/condition_
monitoring_reading already enforce downstream: HISTORICAL_PM_OCCURRENCE_
CANDIDATE, HISTORICAL_CMON_READING_CANDIDATE, and
HISTORICAL_FINDING_CANDIDATE (a Finding row is staged on its own, never
auto-merged into a CMON candidate's `finding` field at extraction time --
see migration 015's own comment: every real pump tag has multiple dated
CM readings per monthly report, so which specific reading a finding
belongs to cannot be safely inferred; a human reviewer attaches it
explicitly). Never HISTORICAL_CM_REPORT_* -- this pipeline never writes
cm_report (Corrective Maintenance), per this MWO's own Semantic Freeze.

extraction_provider is honestly 'deterministic_workbook_table_parser' (not
'claude', the column's own default) -- no AI/document-intelligence service
is used anywhere in this pipeline; every extracted value comes from a
plain, deterministic openpyxl cell read of the source workbook. Per
Phase 20's own rule, AI is never authoritative here because AI is not
used at all.

status follows installation_review_service.py's own real state machine
(PENDING_REVIEW -> REVIEWED -> SAVED, or -> REJECTED) unmodified --
reused via validate_status_transition, not reimplemented.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .installation_review_service import validate_status_transition  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

PM_OCCURRENCE_CANDIDATE = "HISTORICAL_PM_OCCURRENCE_CANDIDATE"
CMON_READING_CANDIDATE = "HISTORICAL_CMON_READING_CANDIDATE"
FINDING_CANDIDATE = "HISTORICAL_FINDING_CANDIDATE"
EXTRACTION_PROVIDER = "deterministic_workbook_table_parser"

_SELECT_COLUMNS = (
    "document_field_extraction_id, source_document_id, source_document_type, "
    "detected_document_type, detected_document_type_confidence, extraction_provider, "
    "ocr_text, extracted_fields, reviewed_fields, status, pump_tag_number, seal_code, "
    "source_page, reviewed_by, reviewed_at, created_at, updated_at"
)


class InvalidStatusTransitionError(ValueError):
    pass


class HistoricalPMCMONStagingRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def create_candidate(
        self,
        *,
        source_document_id: str,
        detected_document_type: str,
        extracted_fields: dict,
        pump_tag_number: str | None = None,
        source_page: int | None = None,
    ) -> dict:
        candidate_id = f"DFE-{uuid.uuid4().hex[:16].upper()}"
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO document_field_extraction "
                "(document_field_extraction_id, source_document_id, source_document_type, "
                "detected_document_type, extraction_provider, extracted_fields, status, "
                "pump_tag_number, source_page) VALUES "
                f"({_sql(candidate_id)}, {_sql(source_document_id)}, 'PDF', "
                f"{_sql(detected_document_type)}, {_sql(EXTRACTION_PROVIDER)}, "
                f"{_sql(json.dumps(extracted_fields))}::jsonb, 'PENDING_REVIEW', "
                f"{_sql(pump_tag_number)}, {_sql(source_page)}) "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

    def find_by_id(self, candidate_id: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM document_field_extraction "
            f"WHERE document_field_extraction_id = {_sql(candidate_id)}",
            self._runner,
        )
        return rows[0] if rows else None

    def find_by_ids(self, candidate_ids: list[str]) -> list[dict]:
        # MWO-LTSA-RECOVERY-STATUS-LATENCY-001 -- batched sibling of
        # find_by_id(), read-only, ONE query for many ids. Exists so a
        # caller validating N candidates (historical_pm_promotion_batch_
        # service.validate_promotion_batch()) never has to call find_by_id()
        # once per candidate -- that N-round-trip pattern measured at
        # ~1,624 fresh-connection queries for N=540 in production
        # (~54s), which is what made GET .../recovery/pm/status
        # routinely exceed the frontend's default 15s timeout.
        if not candidate_ids:
            return []
        values = ", ".join(_sql(cid) for cid in candidate_ids)
        return _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM document_field_extraction "
            f"WHERE document_field_extraction_id IN ({values})",
            self._runner,
        )

    def list_pending(self, detected_document_type: str | None = None) -> list[dict]:
        return self.list_by_status("PENDING_REVIEW", detected_document_type)

    def list_by_status(self, status: str, detected_document_type: str | None = None) -> list[dict]:
        # MWO-LTSA-HISTORICAL-INCOMPLETE-DATA-POLICY-001 -- generalizes
        # list_pending() (unchanged, still PENDING_REVIEW-only) so an
        # INCOMPLETE observation that has already been reviewed (status
        # REVIEWED, pump_tag_number still NULL -- not yet promotable)
        # remains discoverable in Historical Review after a page reload,
        # not just within one browser session's own local state.
        where = f"status = {_sql(status)}"
        if detected_document_type:
            where += f" AND detected_document_type = {_sql(detected_document_type)}"
        return _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM document_field_extraction WHERE {where} "
            "ORDER BY created_at ASC",
            self._runner,
        )

    def list_for_source(self, source_document_id: str) -> list[dict]:
        return _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM document_field_extraction "
            f"WHERE source_document_id = {_sql(source_document_id)} "
            "ORDER BY source_page ASC NULLS LAST, created_at ASC",
            self._runner,
        )

    def apply_review(
        self,
        candidate_id: str,
        *,
        reviewed_fields: dict,
        reviewed_by: str,
        next_status: str = "REVIEWED",
        pump_tag_number: str | None = None,
    ) -> dict | None:
        """Applies a human reviewer's correction. `reviewed_fields` is
        stored SEPARATELY from `extracted_fields` -- the original
        extraction is never overwritten (Phase 13's own explicit
        requirement: SOURCE-EXTRACTED VALUE vs HUMAN-CORRECTED VALUE,
        both retained)."""
        current = self.find_by_id(candidate_id)
        if current is None:
            return None
        if not validate_status_transition(current["status"], next_status):
            raise InvalidStatusTransitionError(
                f"cannot transition {current['status']!r} -> {next_status!r}"
            )

        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE document_field_extraction SET "
                f"reviewed_fields = {_sql(json.dumps(reviewed_fields))}::jsonb, "
                f"status = {_sql(next_status)}, "
                f"reviewed_by = {_sql(reviewed_by)}, reviewed_at = NOW(), "
                f"pump_tag_number = COALESCE({_sql(pump_tag_number)}, pump_tag_number), "
                f"updated_at = NOW() "
                f"WHERE document_field_extraction_id = {_sql(candidate_id)} "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def reject(self, candidate_id: str, *, reviewed_by: str) -> dict | None:
        current = self.find_by_id(candidate_id)
        if current is None:
            return None
        if not validate_status_transition(current["status"], "REJECTED"):
            raise InvalidStatusTransitionError(f"cannot reject from {current['status']!r}")
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE document_field_extraction SET "
                "status = 'REJECTED', "
                f"reviewed_by = {_sql(reviewed_by)}, reviewed_at = NOW(), updated_at = NOW() "
                f"WHERE document_field_extraction_id = {_sql(candidate_id)} "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def mark_saved(self, candidate_id: str) -> None:
        self._runner.execute_script(
            "UPDATE document_field_extraction SET status = 'SAVED', updated_at = NOW() "
            f"WHERE document_field_extraction_id = {_sql(candidate_id)};"
        )

    def count_canonical_pump_matches(self, pump_tag_number: str) -> int:
        rows = _json_query(
            f"SELECT count(*) AS n FROM ltsa_pumps WHERE tag_number = {_sql(pump_tag_number)}",
            self._runner,
        )
        return int(rows[0]["n"]) if rows else 0

    def final_pm_occurrence_exists(self, *, asset_code: str, occurrence_date: str) -> bool:
        rows = _json_query(
            "SELECT count(*) AS n FROM pm_occurrence "
            f"WHERE asset_code = {_sql(asset_code)} AND occurrence_date = {_sql(occurrence_date)} "
            "AND deleted_at IS NULL",
            self._runner,
        )
        return bool(rows and int(rows[0]["n"]) > 0)

    def find_by_stable_identity(self, candidate_identity_v2: str) -> dict | None:
        # MWO-LTSA-SELECTIVE-HISTORICAL-STAGING-001 -- no schema change:
        # extracted_fields is already a JSONB column designed to hold
        # exactly this kind of structured candidate data, so the V2
        # stable identity (build_pm_occurrence_code_v2 /
        # build_condition_monitoring_reading_code_v2, ltsa_hoc_pm_cm_
        # upsert.py -- workbook+sheet+row, NOT the legacy V1 sheet+row-only
        # hash that MWO-LTSA-PM-CMON-DETERMINISTIC-ID-FIX-015B1's own
        # comment documents as colliding across different months' files)
        # is stored as extracted_fields->>'candidate_identity_v2' and
        # looked up with a plain JSONB text match. No index needed at this
        # table's real size (low hundreds to low thousands of rows).
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM document_field_extraction "
            f"WHERE extracted_fields->>'candidate_identity_v2' = {_sql(candidate_identity_v2)}",
            self._runner,
        )
        return rows[0] if rows else None

    def stage_verified_batch(self, candidates: list[dict]) -> list[dict]:
        """True single-transaction batch stage for a caller-supplied,
        already-classified candidate list -- never rediscovers or
        reclassifies anything itself. Each candidate dict:
        {candidate_identity_v2, detected_document_type, pump_tag_number,
        extracted_fields (already includes candidate_identity_v2), source_page}.

        Same "one script, one atomic outcome" shape as installation_
        report_repository.backfill_pump_tags_batch_atomic(): BEGIN ->
        DB-side precheck DO block (RAISE EXCEPTION if any candidate's
        stable identity already exists, or its pump_tag_number is set but
        doesn't resolve to exactly one ltsa_pumps row) -> one INSERT ...
        SELECT * FROM (VALUES ...) covering all N rows -> DB-side
        postcheck DO block (RAISE EXCEPTION unless exactly N new rows
        exist) -> COMMIT -> final SELECT. Postgres's own simple-query
        implicit-transaction guarantee (relied on unchanged from the
        installation-attribution fix) makes this atomic with no
        DatabaseRunner change. Every row_id is still a fresh UUID (never
        the dedup key) -- only extracted_fields->>'candidate_identity_v2'
        is the stable identity a rerun is checked against."""
        if not candidates:
            return []

        n = len(candidates)
        rows_values = []
        identities_sql = []
        pump_checks = []
        for c in candidates:
            candidate_id = f"DFE-{uuid.uuid4().hex[:16].upper()}"
            identity = c["candidate_identity_v2"]
            identities_sql.append(_sql(identity))
            pump_tag = c.get("pump_tag_number")
            if pump_tag:
                pump_checks.append(_sql(pump_tag))
            rows_values.append(
                "(" + ", ".join([
                    _sql(candidate_id),
                    _sql(c["source_document_id"]),
                    "'PDF'",
                    _sql(c["detected_document_type"]),
                    _sql(EXTRACTION_PROVIDER),
                    f"{_sql(json.dumps(c['extracted_fields']))}::jsonb",
                    "'PENDING_REVIEW'",
                    _sql(pump_tag),
                    _sql(c.get("source_page")),
                ]) + ")"
            )

        values_sql = ", ".join(rows_values)
        identities_in_sql = ", ".join(identities_sql)
        pump_values_sql = ", ".join(f"({p})" for p in sorted(set(pump_checks))) or "(NULL)"

        script = f"""
BEGIN;

DO $$
DECLARE
  v_dup_identity_count INT;
  v_bad_pump_count INT;
BEGIN
  SELECT count(*) INTO v_dup_identity_count
  FROM document_field_extraction
  WHERE extracted_fields->>'candidate_identity_v2' IN ({identities_in_sql});
  IF v_dup_identity_count > 0 THEN
    RAISE EXCEPTION 'stage_verified_batch precheck failed: % candidate(s) already staged', v_dup_identity_count;
  END IF;

  SELECT count(*) INTO v_bad_pump_count
  FROM (VALUES {pump_values_sql}) AS m(tag)
  LEFT JOIN (SELECT tag_number, count(*) AS c FROM ltsa_pumps GROUP BY tag_number) p
    ON p.tag_number = m.tag
  WHERE m.tag IS NOT NULL AND (p.tag_number IS NULL OR p.c <> 1);
  IF v_bad_pump_count > 0 THEN
    RAISE EXCEPTION 'stage_verified_batch precheck failed: % pump tag(s) unknown/ambiguous', v_bad_pump_count;
  END IF;
END $$;

INSERT INTO document_field_extraction
    (document_field_extraction_id, source_document_id, source_document_type,
     detected_document_type, extraction_provider, extracted_fields, status,
     pump_tag_number, source_page)
VALUES {values_sql};

DO $$
DECLARE
  v_staged_count INT;
BEGIN
  SELECT count(*) INTO v_staged_count
  FROM document_field_extraction
  WHERE extracted_fields->>'candidate_identity_v2' IN ({identities_in_sql});
  IF v_staged_count <> {n} THEN
    RAISE EXCEPTION 'stage_verified_batch postcheck failed: % of {n} staged', v_staged_count;
  END IF;
END $$;

COMMIT;

SELECT COALESCE((SELECT json_agg(row_to_json(t))::text FROM (
    SELECT {_SELECT_COLUMNS} FROM document_field_extraction
    WHERE extracted_fields->>'candidate_identity_v2' IN ({identities_in_sql})
) t), '[]');
"""
        raw = self._runner.query_scalar(script.strip())
        return json.loads(raw or "[]")

    def bulk_review_batch_atomic(self, candidate_ids: list[str], *, reviewed_by: str) -> list[dict]:
        """MWO-LTSA-BULK-HISTORICAL-REVIEW-001 -- true single-transaction
        bulk "confirm as extracted" for an explicit, caller-supplied
        candidate_id list. Never rediscovers which candidates to touch,
        never corrects a field (reviewed_fields is copied from
        extracted_fields verbatim -- the source-extracted value is never
        altered), PM-only, PENDING_REVIEW-only. Same "one script, one
        atomic outcome" idiom as stage_verified_batch()/installation_
        report_repository.backfill_pump_tags_batch_atomic(): BEGIN ->
        precheck DO block (RAISE EXCEPTION unless every id currently
        exists with status='PENDING_REVIEW' AND detected_document_type=
        'HISTORICAL_PM_OCCURRENCE_CANDIDATE') -> one UPDATE ... WHERE id
        IN (...) -> postcheck DO block (RAISE EXCEPTION unless exactly N
        rows are now REVIEWED) -> COMMIT -> final SELECT."""
        if not candidate_ids:
            return []

        n = len(candidate_ids)
        ids_sql = ", ".join(_sql(cid) for cid in candidate_ids)

        script = f"""
BEGIN;

DO $$
DECLARE
  v_eligible_count INT;
BEGIN
  SELECT count(*) INTO v_eligible_count
  FROM document_field_extraction
  WHERE document_field_extraction_id IN ({ids_sql})
    AND status = 'PENDING_REVIEW'
    AND detected_document_type = '{PM_OCCURRENCE_CANDIDATE}';
  IF v_eligible_count <> {n} THEN
    RAISE EXCEPTION 'bulk_review_batch_atomic precheck failed: % of % candidate(s) eligible (PENDING_REVIEW + PM only)', v_eligible_count, {n};
  END IF;
END $$;

UPDATE document_field_extraction
SET status = 'REVIEWED',
    reviewed_fields = extracted_fields,
    reviewed_by = {_sql(reviewed_by)},
    reviewed_at = NOW(),
    updated_at = NOW()
WHERE document_field_extraction_id IN ({ids_sql})
  AND status = 'PENDING_REVIEW'
  AND detected_document_type = '{PM_OCCURRENCE_CANDIDATE}';

DO $$
DECLARE
  v_reviewed_count INT;
BEGIN
  SELECT count(*) INTO v_reviewed_count
  FROM document_field_extraction
  WHERE document_field_extraction_id IN ({ids_sql})
    AND status = 'REVIEWED';
  IF v_reviewed_count <> {n} THEN
    RAISE EXCEPTION 'bulk_review_batch_atomic postcheck failed: % of {n} reviewed', v_reviewed_count;
  END IF;
END $$;

COMMIT;

SELECT COALESCE((SELECT json_agg(row_to_json(t))::text FROM (
    SELECT {_SELECT_COLUMNS} FROM document_field_extraction
    WHERE document_field_extraction_id IN ({ids_sql})
) t), '[]');
"""
        raw = self._runner.query_scalar(script.strip())
        return json.loads(raw or "[]")


__all__ = [
    "HistoricalPMCMONStagingRepository",
    "InvalidStatusTransitionError",
    "PM_OCCURRENCE_CANDIDATE",
    "CMON_READING_CANDIDATE",
    "FINDING_CANDIDATE",
    "EXTRACTION_PROVIDER",
]
