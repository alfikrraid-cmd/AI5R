"""MWO-LTSA-PM-CM-INTAKE-001 -- real PM Occurrence persistence: create
draft, read, update draft, submit, TAP administrative review, John Crane
technical review.

Direct-Postgres, not PMOccurrenceGateway/n8n: the gateway is deliberately
append-only (create/get/list only, per WO-PMOCC-001/ADR-PM-OCCURRENCE-001
-- no n8n update workflow exists to route an edit/submit/review action
through), and this MWO's own draft-edit-submit-review lifecycle needs
real UPDATE statements this session has no way to prove work through an
n8n workflow JSON (no live n8n round-trip testing available, unlike
disposable Postgres). Reuses the exact DatabaseRunner/_json_query/_sql
machinery auth_repository.py/seal_master_data_repository.py already
established for this same situation.

Every workflow_status transition is additionally guarded by a WHERE
clause on the current workflow_status (defense in depth alongside the
router/service-level pm_cm_workflow_service check) -- an UPDATE that
targets a record no longer in the expected state simply matches zero
rows and returns None, never silently succeeds against a stale state.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .pm_cm_workflow_service import DRAFT, RETURNED_FOR_CORRECTION  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

_EDITABLE_STATUSES_SQL = f"({_sql(DRAFT)}, {_sql(RETURNED_FOR_CORRECTION)})"

_SELECT_COLUMNS = (
    "pm_occurrence_code, pm_schedule_code, asset_code, asset_type, occurrence_date, "
    "status, checklist_completion, work_order_code, activities, finding, "
    "preliminary_recommendation, remarks, provenance, workflow_status, "
    "submitted_by, submitted_at, reviewed_by, reviewed_at, return_reason, "
    "technical_reviewed_by, technical_reviewed_at, technical_outcome, "
    "technical_comment, technical_recommendation, created_by, updated_by, "
    "created_at, updated_at, source_reference, deleted_at, deleted_by"
)


def _new_code() -> str:
    return f"PMOCC-{uuid.uuid4().hex[:12].upper()}"


class PMOccurrenceRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def find_by_code(self, pm_occurrence_code: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM pm_occurrence WHERE pm_occurrence_code = {_sql(pm_occurrence_code)} AND deleted_at IS NULL",
            self._runner,
        )
        return rows[0] if rows else None

    def list_by_asset(self, asset_code: str) -> list[dict]:
        return _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM pm_occurrence WHERE asset_code = {_sql(asset_code)} AND deleted_at IS NULL "
            "ORDER BY occurrence_date DESC NULLS LAST, created_at DESC",
            self._runner,
        )

    def list_all(self, *, scope: frozenset[str] | None = None, limit: int = 5000, offset: int = 0) -> list[dict]:
        # MWO-LTSA-FLEET-ANALYTICS-001 -- fleet-wide batch fetch, mirroring
        # condition_monitoring_reading_repository.list_all()'s own exact
        # shape (LEFT JOIN ltsa_pumps for area, same scope-filter
        # convention) so a fleet scan fetches every asset's PM occurrences
        # in ONE query instead of one list_by_asset() call per pump. limit
        # defaults generously (5000, matching this repository's own
        # "generous but bounded" convention elsewhere in this codebase,
        # e.g. PMCMEvidenceRepository's own MAX_FILE_SIZE_BYTES) -- a
        # caller needing true pagination can still lower it/page with
        # offset; this is a read-only, additive method, no change to any
        # existing method's behavior.
        scope_clause = ""
        if scope is not None:
            if scope:
                values = ", ".join(_sql(area) for area in sorted(scope))
                scope_clause = f"AND pump.area IN ({values})"
            else:
                scope_clause = "AND FALSE"
        columns = ", ".join(f"r.{col}" for col in _SELECT_COLUMNS.split(", "))
        return _json_query(
            f"SELECT {columns}, pump.area "
            "FROM pm_occurrence r LEFT JOIN ltsa_pumps pump ON pump.tag_number = r.asset_code "
            f"WHERE r.deleted_at IS NULL {scope_clause} "
            "ORDER BY r.occurrence_date DESC NULLS LAST, r.created_at DESC "
            f"LIMIT {int(limit)} OFFSET {int(offset)}",
            self._runner,
        )

    def create_draft(
        self,
        *,
        pm_schedule_code: str,
        asset_code: str,
        asset_type: str | None,
        occurrence_date: str | None,
        activities: list | None,
        remarks: str | None,
        created_by: str,
        provenance: str = "MANUAL",
        source_reference: str | None = None,
    ) -> dict:
        # Hard Rule 14/16: created_by is set once, here, and never
        # referenced again by update_draft/submit/review below --
        # updated_by starts equal to created_by (the creator is trivially
        # also the first "last editor"), the same convention
        # auth_repository.create_user already established.
        #
        # MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- provenance/
        # source_reference are additive, optional kwargs (default
        # 'MANUAL'/None, byte-identical to every pre-existing caller's
        # behavior). The historical-import promotion service is the only
        # caller that passes provenance='HISTORICAL_IMPORT' plus a real
        # source_reference; the live TAP Engineer UI path (PM.jsx via
        # createPMOccurrence) never passes either, so its INSERTs are
        # unchanged.
        code = _new_code()
        # MWO-LTSA-HISTORICAL-PM-RECOVERY-001 -- historical_pm_cmon_
        # promotion_service.promote_pm_occurrence_candidate()'s own
        # documented contract (and build_unscheduled_reference()'s own
        # docstring, ltsa_hoc_pm_cm_upsert.py) says a historical import's
        # pm_schedule_code is the self-disclosing "UNSCHEDULED::<source>"
        # placeholder and "never inserted into pm_schedule" -- but this
        # INSERT's own EXISTS guard below required a REAL pm_schedule row
        # unconditionally, so no historical promotion could ever succeed
        # against an empty pm_schedule table (confirmed: 0 rows in
        # production; not a hypothetical). The guard's real purpose --
        # requiring a genuine schedule for a genuinely scheduled
        # occurrence -- only ever applied to the live TAP Engineer UI path
        # (PM.jsx), which never uses this literal prefix and is completely
        # unaffected: this only widens the WHERE for the placeholder
        # convention already designed to bypass it.
        _requires_real_schedule = not pm_schedule_code.startswith("UNSCHEDULED::")
        _schedule_guard = (
            f"AND EXISTS (SELECT 1 FROM pm_schedule WHERE pm_schedule_code = {_sql(pm_schedule_code)}) "
            if _requires_real_schedule
            else ""
        )
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO pm_occurrence "
                "(pm_occurrence_code, pm_schedule_code, asset_code, asset_type, occurrence_date, "
                "activities, remarks, workflow_status, provenance, created_by, updated_by, source_reference) "
                # Production reproduction fix (mirrors condition_monitoring_
                # reading_repository.py's identical fix) -- this is an
                # INSERT...SELECT (required to carry the WHERE EXISTS gate
                # below, which a plain VALUES tuple cannot), never
                # INSERT...VALUES. A stray "VALUES " token before SELECT was
                # a hard Postgres syntax error (SQLSTATE 42601) on every
                # call -- reproduced against the real canonical schema,
                # never caught by any Fake-runner test (FakeRunner only
                # records the SQL text, never executes it). RETURNING must
                # also sit inside the `ins` CTE's own parens (immediately
                # after the WHERE clause), not after its closing paren --
                # it was previously misplaced there too, a second syntax
                # error masked by the first.
                f"SELECT {_sql(code)}, {_sql(pm_schedule_code)}, {_sql(asset_code)}, {_sql(asset_type)}, "
                f"{_sql(occurrence_date)}, {_sql(json.dumps(activities) if activities is not None else None)}::jsonb, "
                f"{_sql(remarks)}, {_sql(DRAFT)}, {_sql(provenance)}, {_sql(created_by)}, {_sql(created_by)}, "
                f"{_sql(source_reference)} WHERE EXISTS (SELECT 1 FROM ltsa_pumps WHERE tag_number = {_sql(asset_code)}) "
                f"{_schedule_guard}"
                f"RETURNING {_SELECT_COLUMNS}"
                # MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- "Actual PM
                # record is created -> Schedule becomes COMPLETED -> Schedule
                # disappears from active queue", atomically: one INSERT into
                # pm_occurrence and one UPDATE on its owning pm_schedule in
                # the SAME statement/transaction, never two separate round
                # trips that could leave one written without the other. The
                # subquery reads pm_schedule_code from `ins` itself (never
                # the raw pm_schedule_code parameter) so this UPDATE only
                # ever runs when the INSERT above actually matched a row
                # (WHERE pm_schedule_code = NULL matches nothing if `ins`
                # produced zero rows -- pump/schedule not found). The
                # status-guard (NOT IN CANCELLED/COMPLETED) makes recording
                # a second occurrence against an already-completed schedule
                # a safe no-op here rather than an error or a silently
                # re-fired completion.
                "), schedule_completion AS ("
                "UPDATE pm_schedule SET status = 'COMPLETED', updated_by = "
                f"{_sql(created_by)}, updated_at = NOW() "
                "WHERE pm_schedule_code = (SELECT pm_schedule_code FROM ins) "
                "AND status NOT IN ('CANCELLED', 'COMPLETED') "
                "RETURNING pm_schedule_code"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'PM_OCCURRENCE', pm_occurrence_code, '__record__', NULL, "
                "row_to_json(ins)::text, created_by, 'CREATE' FROM ins"
                "), schedule_audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'PM_SCHEDULE', pm_schedule_code, 'status', NULL, 'COMPLETED', "
                f"{_sql(created_by)}, 'AUTO_COMPLETE_ON_OCCURRENCE' FROM schedule_completion) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

    def promote_historical_pm_atomic(
        self,
        candidate_id: str,
        *,
        pm_schedule_code: str,
        promoted_by: str,
    ) -> dict:
        """MWO-LTSA-ATOMIC-PM-PROMOTION-001 -- fixes the two-separate-
        writes defect in the old promote_pm_occurrence_candidate()
        (create_draft() INSERT, then a SEPARATE mark_saved() UPDATE): one
        single Postgres statement (a WITH-chain, same shape as
        create_draft's own ins/schedule_completion CTEs -- Postgres's own
        per-statement atomicity guarantee, no explicit BEGIN/COMMIT
        needed) that re-reads the candidate FOR UPDATE (locks it against
        a concurrent promote of the same id), validates it, checks for an
        existing promotion or conflict, inserts pm_occurrence, and marks
        the candidate SAVED -- all or nothing.

        Retry-safe idempotency key: source_reference =
        'document_field_extraction:<candidate_id>' -- an EXISTING column
        (pm_occurrence.source_reference) and an EXISTING lookup pattern
        (find_by_source_reference(), already proven for the WhatsApp PM
        writer's own idempotency). No schema change: candidate_id is
        assigned once at staging time and is 1:1 stably bound to
        extracted_fields->>'candidate_identity_v2' by
        stage_verified_batch()'s own duplicate-identity precheck, so a
        source_reference lookup is equivalent to a candidate_identity_v2
        lookup without a second index/column.

        Returns a dict:
          candidate_found: bool
          eligible: bool (REVIEWED, PM-type-caller's responsibility to
                    only call this for PM, resolved pump, occurrence_date set)
          already: the existing pm_occurrence row if this exact candidate
                    was already promoted (safe no-op retry), else None
          conflict: an existing pm_occurrence row for the same
                    (asset_code, occurrence_date) from a DIFFERENT
                    candidate, else None
          inserted: the newly-inserted pm_occurrence row, else None
          marked_saved: bool -- True only when the candidate was
                    transitioned REVIEWED -> SAVED in this same statement
        """
        source_reference = f"document_field_extraction:{candidate_id}"
        _requires_real_schedule = not pm_schedule_code.startswith("UNSCHEDULED::")
        _schedule_guard = (
            f"AND EXISTS (SELECT 1 FROM pm_schedule WHERE pm_schedule_code = {_sql(pm_schedule_code)}) "
            if _requires_real_schedule
            else ""
        )
        code = _new_code()
        raw = self._runner.query_scalar(f"""
WITH cand AS (
    SELECT document_field_extraction_id, status, detected_document_type, pump_tag_number,
           COALESCE(reviewed_fields, extracted_fields) AS fields
    FROM document_field_extraction
    WHERE document_field_extraction_id = {_sql(candidate_id)}
    FOR UPDATE
),
eligible AS (
    SELECT * FROM cand
    WHERE status = 'REVIEWED'
      AND detected_document_type = 'HISTORICAL_PM_OCCURRENCE_CANDIDATE'
      AND pump_tag_number IS NOT NULL
      AND fields->>'occurrence_date' IS NOT NULL
),
already AS (
    SELECT {_SELECT_COLUMNS} FROM pm_occurrence
    WHERE source_reference = {_sql(source_reference)} AND deleted_at IS NULL
),
conflict AS (
    SELECT {_SELECT_COLUMNS} FROM pm_occurrence
    WHERE deleted_at IS NULL
      AND source_reference IS DISTINCT FROM {_sql(source_reference)}
      AND asset_code = (SELECT pump_tag_number FROM eligible)
      AND occurrence_date = (SELECT (fields->>'occurrence_date')::date FROM eligible)
),
ins AS (
    INSERT INTO pm_occurrence
        (pm_occurrence_code, pm_schedule_code, asset_code, asset_type, occurrence_date,
         activities, remarks, workflow_status, provenance, created_by, updated_by, source_reference)
    SELECT {_sql(code)}, {_sql(pm_schedule_code)}, e.pump_tag_number,
           COALESCE(e.fields->>'asset_type', 'PUMP'), (e.fields->>'occurrence_date')::date,
           e.fields->'activities', e.fields->>'remarks',
           'DRAFT', 'HISTORICAL_IMPORT', {_sql(promoted_by)}, {_sql(promoted_by)}, {_sql(source_reference)}
    FROM eligible e
    WHERE NOT EXISTS (SELECT 1 FROM already)
      AND NOT EXISTS (SELECT 1 FROM conflict)
      AND EXISTS (SELECT 1 FROM ltsa_pumps WHERE tag_number = e.pump_tag_number)
      {_schedule_guard}
    RETURNING {_SELECT_COLUMNS}
),
mark_saved AS (
    UPDATE document_field_extraction
    SET status = 'SAVED', updated_at = NOW()
    WHERE document_field_extraction_id = {_sql(candidate_id)}
      AND EXISTS (SELECT 1 FROM ins)
    RETURNING document_field_extraction_id
),
audit AS (
    INSERT INTO record_change_history
        (entity_type, entity_id, field_name, old_value, new_value, changed_by, reason)
    SELECT 'PM_OCCURRENCE', pm_occurrence_code, '__record__', NULL, row_to_json(ins)::text,
           {_sql(promoted_by)}, 'HISTORICAL_PROMOTE'
    FROM ins
)
SELECT json_build_object(
    'candidate_found', (SELECT count(*) FROM cand) > 0,
    'eligible', (SELECT count(*) FROM eligible) > 0,
    'already', (SELECT row_to_json(a) FROM already a),
    'conflict', (SELECT row_to_json(k) FROM conflict k),
    'inserted', (SELECT row_to_json(i) FROM ins i),
    'marked_saved', (SELECT count(*) FROM mark_saved) > 0
)::text;
""")
        return json.loads(raw) if raw else {
            "candidate_found": False, "eligible": False, "already": None,
            "conflict": None, "inserted": None, "marked_saved": False,
        }

    def promote_historical_pm_batch_atomic(
        self,
        candidate_ids: list[str],
        *,
        pm_schedule_code: str,
        promoted_by: str,
    ) -> list[dict]:
        """Exact-batch sibling of promote_historical_pm_atomic() -- same
        idempotency key (source_reference), same eligibility rule, same
        conflict rule, but as ONE explicit transaction (BEGIN/DO-
        precheck/INSERT/UPDATE/DO-postcheck/COMMIT/SELECT, the same idiom
        as stage_verified_batch()/bulk_review_batch_atomic()) covering
        every id in `candidate_ids` at once: either every NEW-eligible
        candidate promotes and every already-promoted id stays a safe
        no-op, or NOTHING commits. Never rediscovers membership -- the
        caller supplies the exact frozen id list; historical_pm_
        promotion_batch_service.py is responsible for read-only
        prevalidating that list before calling this.
        """
        if not candidate_ids:
            return []

        n = len(candidate_ids)
        ids_sql = ", ".join(_sql(cid) for cid in candidate_ids)
        _requires_real_schedule = not pm_schedule_code.startswith("UNSCHEDULED::")
        _schedule_guard = (
            f"AND EXISTS (SELECT 1 FROM pm_schedule WHERE pm_schedule_code = {_sql(pm_schedule_code)}) "
            if _requires_real_schedule
            else ""
        )

        script = f"""
BEGIN;

DO $$
DECLARE
  v_ineligible_count INT;
  v_bad_pump_count INT;
  v_conflict_count INT;
BEGIN
  -- Every id must exist, be PM, be REVIEWED or already SAVED (a SAVED id
  -- is allowed into a retry batch -- it is simply a safe no-op below),
  -- have a resolved pump and an occurrence_date.
  SELECT count(*) INTO v_ineligible_count
  FROM document_field_extraction d
  WHERE d.document_field_extraction_id IN ({ids_sql})
    AND NOT (
      d.detected_document_type = 'HISTORICAL_PM_OCCURRENCE_CANDIDATE'
      AND d.status IN ('REVIEWED', 'SAVED')
      AND d.pump_tag_number IS NOT NULL
      AND COALESCE(d.reviewed_fields, d.extracted_fields)->>'occurrence_date' IS NOT NULL
    );
  IF (SELECT count(*) FROM document_field_extraction WHERE document_field_extraction_id IN ({ids_sql})) <> {n}
     OR v_ineligible_count > 0 THEN
    RAISE EXCEPTION 'promotion batch precheck failed: % of % candidate(s) missing/ineligible', v_ineligible_count, {n};
  END IF;

  SELECT count(*) INTO v_bad_pump_count
  FROM (SELECT DISTINCT d.pump_tag_number AS tag FROM document_field_extraction d
        WHERE d.document_field_extraction_id IN ({ids_sql})) m
  LEFT JOIN (SELECT tag_number, count(*) AS c FROM ltsa_pumps GROUP BY tag_number) p
    ON p.tag_number = m.tag
  WHERE p.tag_number IS NULL OR p.c <> 1;
  IF v_bad_pump_count > 0 THEN
    RAISE EXCEPTION 'promotion batch precheck failed: % pump tag(s) unknown/ambiguous', v_bad_pump_count;
  END IF;

  SELECT count(*) INTO v_conflict_count
  FROM document_field_extraction d
  JOIN pm_occurrence p
    ON p.asset_code = d.pump_tag_number
   AND p.occurrence_date = (COALESCE(d.reviewed_fields, d.extracted_fields)->>'occurrence_date')::date
   AND p.deleted_at IS NULL
   AND p.source_reference IS DISTINCT FROM ('document_field_extraction:' || d.document_field_extraction_id)
  WHERE d.document_field_extraction_id IN ({ids_sql});
  IF v_conflict_count > 0 THEN
    RAISE EXCEPTION 'promotion batch precheck failed: % candidate(s) conflict with an existing pm_occurrence for the same asset/date', v_conflict_count;
  END IF;
END $$;

WITH ins AS (
    INSERT INTO pm_occurrence
        (pm_occurrence_code, pm_schedule_code, asset_code, asset_type, occurrence_date,
         activities, remarks, workflow_status, provenance, created_by, updated_by, source_reference)
    SELECT
        'PMOCC-' || upper(substr(md5(d.document_field_extraction_id || clock_timestamp()::text || random()::text), 1, 12)),
        {_sql(pm_schedule_code)}, d.pump_tag_number,
        COALESCE(COALESCE(d.reviewed_fields, d.extracted_fields)->>'asset_type', 'PUMP'),
        (COALESCE(d.reviewed_fields, d.extracted_fields)->>'occurrence_date')::date,
        COALESCE(d.reviewed_fields, d.extracted_fields)->'activities',
        COALESCE(d.reviewed_fields, d.extracted_fields)->>'remarks',
        'DRAFT', 'HISTORICAL_IMPORT', {_sql(promoted_by)}, {_sql(promoted_by)},
        'document_field_extraction:' || d.document_field_extraction_id
    FROM document_field_extraction d
    WHERE d.document_field_extraction_id IN ({ids_sql})
      AND NOT EXISTS (
        SELECT 1 FROM pm_occurrence p2
        WHERE p2.source_reference = 'document_field_extraction:' || d.document_field_extraction_id
          AND p2.deleted_at IS NULL
      )
      {_schedule_guard}
    RETURNING {_SELECT_COLUMNS}
)
INSERT INTO record_change_history
    (entity_type, entity_id, field_name, old_value, new_value, changed_by, reason)
SELECT 'PM_OCCURRENCE', pm_occurrence_code, '__record__', NULL, row_to_json(ins)::text,
       {_sql(promoted_by)}, 'HISTORICAL_PROMOTE_BATCH'
FROM ins;

UPDATE document_field_extraction
SET status = 'SAVED', updated_at = NOW()
WHERE document_field_extraction_id IN ({ids_sql})
  AND status = 'REVIEWED'
  AND EXISTS (
    SELECT 1 FROM pm_occurrence p3
    WHERE p3.source_reference = 'document_field_extraction:' || document_field_extraction_id
      AND p3.deleted_at IS NULL
  );

DO $$
DECLARE
  v_final_count INT;
BEGIN
  SELECT count(*) INTO v_final_count
  FROM document_field_extraction d
  WHERE d.document_field_extraction_id IN ({ids_sql})
    AND d.status = 'SAVED'
    AND EXISTS (
      SELECT 1 FROM pm_occurrence p
      WHERE p.source_reference = 'document_field_extraction:' || d.document_field_extraction_id
        AND p.deleted_at IS NULL
    );
  IF v_final_count <> {n} THEN
    RAISE EXCEPTION 'promotion batch postcheck failed: % of {n} candidate(s) SAVED with a linked pm_occurrence', v_final_count;
  END IF;
END $$;

COMMIT;

SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM (
    SELECT d.document_field_extraction_id, d.status, p.pm_occurrence_code
    FROM document_field_extraction d
    LEFT JOIN pm_occurrence p
      ON p.source_reference = 'document_field_extraction:' || d.document_field_extraction_id
     AND p.deleted_at IS NULL
    WHERE d.document_field_extraction_id IN ({ids_sql})
) t;
"""
        raw = self._runner.query_scalar(script.strip())
        return json.loads(raw or "[]")

    def find_by_asset_and_date(self, asset_code: str, occurrence_date: str) -> dict | None:
        """Read-only. Used by historical_pm_promotion_batch_service.py's
        prevalidation to detect a CONFLICT (a final PM for this (asset,
        date) already exists, produced by a DIFFERENT candidate) before
        the atomic batch write -- (asset_code, occurrence_date) is this
        bounded historical archive's own verified dedup grain, checked
        here only as an additional conflict guard, never as the primary
        retry-identity (that is source_reference, see find_by_source_
        reference below / promote_historical_pm_atomic)."""
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM pm_occurrence "
            f"WHERE asset_code = {_sql(asset_code)} AND occurrence_date = {_sql(occurrence_date)} "
            "AND deleted_at IS NULL LIMIT 1",
            self._runner,
        )
        return rows[0] if rows else None

    def find_by_source_reference(self, source_reference: str) -> dict | None:
        # WhatsApp PM writer readiness (MWO: PM AD-HOC / UNSCHEDULED
        # CANONICAL WRITE DESIGN) -- same durable, DB-backed idempotency
        # lookup purpose as condition_monitoring_reading_repository.py's
        # identical method; source_reference already exists on this table
        # for exactly this "where did this record originate from"
        # traceability purpose, reused unmodified, no schema change.
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM pm_occurrence "
            f"WHERE source_reference = {_sql(source_reference)} AND deleted_at IS NULL LIMIT 1",
            self._runner,
        )
        return rows[0] if rows else None

    def find_open_schedules_by_asset(self, asset_code: str) -> list[dict]:
        # "Open" mirrors create_draft's own existing auto-completion
        # semantics (status NOT IN ('CANCELLED', 'COMPLETED') is exactly
        # what its schedule_completion CTE treats as still eligible to be
        # completed by a new occurrence) -- same convention
        # condition_monitoring_reading_repository.py's identical method
        # already established, against pm_schedule's own pre-existing
        # PLANNED/ACTIVE/OVERDUE/COMPLETED/CANCELLED lifecycle (migration
        # 029's own comment: "the owner-approved ... lifecycle already
        # implemented for pm_schedule").
        return _json_query(
            "SELECT pm_schedule_code, asset_code, asset_type, procedure, frequency, status "
            "FROM pm_schedule "
            f"WHERE asset_code = {_sql(asset_code)} AND status NOT IN ('CANCELLED', 'COMPLETED') "
            "ORDER BY pm_schedule_code",
            self._runner,
        )

    def create_ad_hoc_draft(
        self,
        *,
        asset_code: str,
        asset_type: str | None,
        occurrence_date: str | None,
        activities: list | None,
        remarks: str | None,
        created_by: str,
        source_reference: str,
        provenance: str = "WHATSAPP",
    ) -> dict | None:
        """PM occurrence with no real schedule to link to -- the same
        disclosed 'UNSCHEDULED::<source>' sentinel convention
        PRODUCTS/LTSA-BRAIN/INGESTION/ltsa_hoc_pm_cm_upsert.py's own
        build_unscheduled_reference() already established (and
        ltsa_hoc_pm_cm_db_upsert.py's apply_plan() already ships to
        production with, via its own direct INSERT INTO pm_occurrence --
        this method is the same convention finally exposed through the
        authoritative repository's own write path). pm_occurrence.
        pm_schedule_code is NOT NULL but not FK-constrained to pm_schedule
        (see CANONICAL_SCHEMA.sql's own DDL comment on this table) -- a
        self-disclosing sentinel string satisfies the NOT NULL requirement
        without ever inserting or referencing a fabricated pm_schedule
        row. No schedule_completion CTE, no PM_SCHEDULE audit event --
        there is no real schedule to complete or audit.

        Returns None (no row created, no exception) when asset_code
        doesn't exist -- callers must check for this rather than assume
        success, same contract as create_draft's own WHERE EXISTS-gated
        silent-no-op-on-missing-asset behavior.
        """
        code = _new_code()
        schedule_code = f"UNSCHEDULED::{provenance}"
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO pm_occurrence "
                "(pm_occurrence_code, pm_schedule_code, asset_code, asset_type, occurrence_date, "
                "activities, remarks, workflow_status, provenance, created_by, updated_by, source_reference) "
                f"SELECT {_sql(code)}, {_sql(schedule_code)}, {_sql(asset_code)}, {_sql(asset_type)}, "
                f"{_sql(occurrence_date)}, {_sql(json.dumps(activities) if activities is not None else None)}::jsonb, "
                f"{_sql(remarks)}, {_sql(DRAFT)}, {_sql(provenance)}, {_sql(created_by)}, {_sql(created_by)}, "
                f"{_sql(source_reference)} "
                f"WHERE EXISTS (SELECT 1 FROM ltsa_pumps WHERE tag_number = {_sql(asset_code)}) "
                f"RETURNING {_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'PM_OCCURRENCE', pm_occurrence_code, '__record__', NULL, "
                "row_to_json(ins)::text, created_by, 'CREATE' FROM ins) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def update_draft(
        self,
        pm_occurrence_code: str,
        *,
        occurrence_date: str | None,
        activities: list | None,
        finding: str | None,
        preliminary_recommendation: str | None,
        remarks: str | None,
        updated_by: str,
    ) -> dict | None:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH old AS (SELECT row_to_json(p)::text AS snapshot FROM pm_occurrence p "
                f"WHERE pm_occurrence_code = {_sql(pm_occurrence_code)} AND deleted_at IS NULL), upd AS ("
                "UPDATE pm_occurrence SET "
                f"occurrence_date = {_sql(occurrence_date)}, "
                f"activities = {_sql(json.dumps(activities) if activities is not None else None)}::jsonb, "
                f"finding = {_sql(finding)}, "
                f"preliminary_recommendation = {_sql(preliminary_recommendation)}, "
                f"remarks = {_sql(remarks)}, "
                f"updated_by = {_sql(updated_by)}, updated_at = NOW() "
                f"WHERE pm_occurrence_code = {_sql(pm_occurrence_code)} AND deleted_at IS NULL "
                f"AND workflow_status IN {_EDITABLE_STATUSES_SQL} "
                f"RETURNING {_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'PM_OCCURRENCE', pm_occurrence_code, '__record__', old.snapshot, "
                "row_to_json(upd)::text, updated_by, 'UPDATE' FROM upd CROSS JOIN old) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def submit(self, pm_occurrence_code: str, *, submitted_by: str) -> dict | None:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE pm_occurrence SET "
                "workflow_status = 'SUBMITTED', "
                f"submitted_by = {_sql(submitted_by)}, submitted_at = NOW(), "
                f"updated_by = {_sql(submitted_by)}, updated_at = NOW() "
                f"WHERE pm_occurrence_code = {_sql(pm_occurrence_code)} "
                f"AND workflow_status IN {_EDITABLE_STATUSES_SQL} "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def admin_return_for_correction(
        self, pm_occurrence_code: str, *, reviewed_by: str, return_reason: str
    ) -> dict | None:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE pm_occurrence SET "
                "workflow_status = 'RETURNED_FOR_CORRECTION', "
                f"reviewed_by = {_sql(reviewed_by)}, reviewed_at = NOW(), "
                f"return_reason = {_sql(return_reason)}, "
                f"updated_by = {_sql(reviewed_by)}, updated_at = NOW() "
                f"WHERE pm_occurrence_code = {_sql(pm_occurrence_code)} AND deleted_at IS NULL AND workflow_status = 'SUBMITTED' "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def soft_delete(self, pm_occurrence_code: str, *, deleted_by: str) -> dict | None:
        rows = json.loads(self._runner.query_scalar(
            "WITH old AS (SELECT row_to_json(p)::text AS snapshot FROM pm_occurrence p "
            f"WHERE pm_occurrence_code = {_sql(pm_occurrence_code)} AND deleted_at IS NULL), upd AS (UPDATE pm_occurrence SET deleted_at = NOW(), deleted_by = "
            f"{_sql(deleted_by)}, updated_by = {_sql(deleted_by)}, updated_at = NOW() "
            f"WHERE pm_occurrence_code = {_sql(pm_occurrence_code)} AND deleted_at IS NULL "
            f"RETURNING {_SELECT_COLUMNS}), audit AS (INSERT INTO record_change_history "
            "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
            "SELECT 'PM_OCCURRENCE', pm_occurrence_code, '__record__', old.snapshot, NULL, "
            f"{_sql(deleted_by)}, 'DELETE' FROM upd CROSS JOIN old) SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
        ) or "[]")
        return rows[0] if rows else None

    def technical_return_for_correction(
        self, pm_occurrence_code: str, *, technical_reviewed_by: str, technical_comment: str
    ) -> dict | None:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE pm_occurrence SET "
                "workflow_status = 'RETURNED_FOR_CORRECTION', "
                f"technical_reviewed_by = {_sql(technical_reviewed_by)}, technical_reviewed_at = NOW(), "
                f"technical_comment = {_sql(technical_comment)}, "
                f"updated_by = {_sql(technical_reviewed_by)}, updated_at = NOW() "
                f"WHERE pm_occurrence_code = {_sql(pm_occurrence_code)} AND workflow_status = 'SUBMITTED' "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def technical_finalize(
        self,
        pm_occurrence_code: str,
        *,
        technical_reviewed_by: str,
        technical_outcome: str,
        technical_comment: str | None,
        technical_recommendation: str | None,
    ) -> dict | None:
        # Phase 14: technical_recommendation is its own column, distinct
        # from preliminary_recommendation -- this UPDATE never touches
        # preliminary_recommendation, so TAP's own field recommendation
        # can never be silently overwritten by John Crane's action.
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE pm_occurrence SET "
                "workflow_status = 'FINALIZED', "
                f"technical_reviewed_by = {_sql(technical_reviewed_by)}, technical_reviewed_at = NOW(), "
                f"technical_outcome = {_sql(technical_outcome)}, "
                f"technical_comment = {_sql(technical_comment)}, "
                f"technical_recommendation = {_sql(technical_recommendation)}, "
                f"updated_by = {_sql(technical_reviewed_by)}, updated_at = NOW() "
                f"WHERE pm_occurrence_code = {_sql(pm_occurrence_code)} AND workflow_status = 'SUBMITTED' "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None


__all__ = ["PMOccurrenceRepository"]
