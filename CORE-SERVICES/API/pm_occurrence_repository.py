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
    "created_at, updated_at"
)


def _new_code() -> str:
    return f"PMOCC-{uuid.uuid4().hex[:12].upper()}"


class PMOccurrenceRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def find_by_code(self, pm_occurrence_code: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM pm_occurrence WHERE pm_occurrence_code = {_sql(pm_occurrence_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_by_asset(self, asset_code: str) -> list[dict]:
        return _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM pm_occurrence WHERE asset_code = {_sql(asset_code)} "
            "ORDER BY occurrence_date DESC NULLS LAST, created_at DESC",
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
    ) -> dict:
        # Hard Rule 14/16: created_by is set once, here, and never
        # referenced again by update_draft/submit/review below --
        # updated_by starts equal to created_by (the creator is trivially
        # also the first "last editor"), the same convention
        # auth_repository.create_user already established.
        code = _new_code()
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO pm_occurrence "
                "(pm_occurrence_code, pm_schedule_code, asset_code, asset_type, occurrence_date, "
                "activities, remarks, workflow_status, provenance, created_by, updated_by) VALUES "
                f"({_sql(code)}, {_sql(pm_schedule_code)}, {_sql(asset_code)}, {_sql(asset_type)}, "
                f"{_sql(occurrence_date)}, {_sql(json.dumps(activities) if activities is not None else None)}::jsonb, "
                f"{_sql(remarks)}, {_sql(DRAFT)}, 'MANUAL', {_sql(created_by)}, {_sql(created_by)}) "
                f"RETURNING {_SELECT_COLUMNS}"
                f") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

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
                "WITH upd AS ("
                "UPDATE pm_occurrence SET "
                f"occurrence_date = {_sql(occurrence_date)}, "
                f"activities = {_sql(json.dumps(activities) if activities is not None else None)}::jsonb, "
                f"finding = {_sql(finding)}, "
                f"preliminary_recommendation = {_sql(preliminary_recommendation)}, "
                f"remarks = {_sql(remarks)}, "
                f"updated_by = {_sql(updated_by)}, updated_at = NOW() "
                f"WHERE pm_occurrence_code = {_sql(pm_occurrence_code)} "
                f"AND workflow_status IN {_EDITABLE_STATUSES_SQL} "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
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
                f"WHERE pm_occurrence_code = {_sql(pm_occurrence_code)} AND workflow_status = 'SUBMITTED' "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
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
