"""MWO-LTSA-PM-CM-INTAKE-001 -- real Condition Monitoring Reading
persistence: create draft, read, update draft, submit, TAP administrative
review, John Crane technical review.

Direct-Postgres, not ConditionMonitoringReadingGateway/n8n -- identical
reasoning to pm_occurrence_repository.py's own header (the gateway is
deliberately append-only per WO-CMON-001, no n8n update workflow exists).
Same workflow_status vocabulary/transitions as PM Occurrence
(pm_cm_workflow_service.py is the one shared state machine for both --
Phase 10's "avoid state explosion"); this file only differs in which
domain-specific measurement columns create_draft/update_draft accept.
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

# Every measurement column this repository's create/update accept --
# matches the golden "Mechanical Seal Condition Monitoring" report's
# Check Points table (this MWO's own Phase 1 audit), split across the
# pre-existing (WO-CMON-001) columns and this MWO's migration-014
# additions. A single tuple so create_draft/update_draft/_SELECT_COLUMNS
# stay in sync by construction, not by hand-copied lists drifting apart.
_MEASUREMENT_COLUMNS = (
    "flushing_temp_de", "flushing_temp_nde",
    "quench_temp_de", "quench_temp_nde",
    "flushing_in_temp_de", "flushing_in_temp_nde",
    "flushing_out_temp_de", "flushing_out_temp_nde",
    "cooling_water_in_temp_de", "cooling_water_in_temp_nde",
    "cooling_water_out_temp_de", "cooling_water_out_temp_nde",
    "mechseal_temp_de", "mechseal_temp_nde",
    "mechanical_seal_leak_de", "mechanical_seal_leak_nde",
    "water_jacket_temp_de", "water_jacket_temp_nde",
    "suction_temp", "discharge_temp",
    "pump_operating_state",
    "suction_pressure", "discharge_pressure",
    "quench_pressure_de", "quench_pressure_nde",
    "stuffing_box_temp_de", "stuffing_box_temp_nde",
    "seal_gland_temp_de", "seal_gland_temp_nde",
    "vertical_vibration_de", "vertical_vibration_nde",
    "horizontal_vibration_de", "horizontal_vibration_nde",
    "axial_vibration_de", "axial_vibration_nde",
    "bearing_temp_de", "bearing_temp_nde",
    "motor_current",
)

_WORKFLOW_COLUMNS = (
    "finding", "provenance", "workflow_status", "submitted_by", "submitted_at",
    "reviewed_by", "reviewed_at", "return_reason", "technical_reviewed_by",
    "technical_reviewed_at", "technical_outcome", "technical_comment",
    "technical_recommendation", "created_by", "updated_by",
)

_SELECT_COLUMNS = (
    "condition_monitoring_reading_code, condition_monitoring_schedule_code, "
    "asset_code, asset_type, reading_date, "
    + ", ".join(_MEASUREMENT_COLUMNS)
    + ", "
    + ", ".join(_WORKFLOW_COLUMNS)
    + ", created_at, updated_at, source_reference"
)


def _new_code() -> str:
    return f"CMONR-{uuid.uuid4().hex[:12].upper()}"


class ConditionMonitoringReadingRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def find_by_code(self, reading_code: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM condition_monitoring_reading "
            f"WHERE condition_monitoring_reading_code = {_sql(reading_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_all(self, *, scope: frozenset[str] | None = None) -> dict:
        scope_clause = ""
        if scope is not None:
            if scope:
                values = ", ".join(_sql(area) for area in sorted(scope))
                scope_clause = f"WHERE pump.area IN ({values})"
            else:
                scope_clause = "WHERE FALSE"
        rows = _json_query(
            "SELECT r.*, pump.area, pump.name AS pump_name "
            "FROM condition_monitoring_reading r "
            "LEFT JOIN ltsa_pumps pump ON pump.tag_number = r.asset_code "
            f"{scope_clause} "
            "ORDER BY r.reading_date DESC NULLS LAST, r.created_at DESC",
            self._runner,
        )
        return {
            "success": True,
            "message": "Condition Monitoring reading list retrieved",
            "count": len(rows),
            "data": rows,
            "items": rows,
        }
    def list_by_asset(self, asset_code: str) -> list[dict]:
        return _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM condition_monitoring_reading "
            f"WHERE asset_code = {_sql(asset_code)} "
            "ORDER BY reading_date DESC NULLS LAST, created_at DESC",
            self._runner,
        )

    def create_draft(
        self,
        *,
        condition_monitoring_schedule_code: str,
        asset_code: str,
        asset_type: str | None,
        reading_date: str | None,
        measurements: dict,
        created_by: str,
        provenance: str = "MANUAL",
        source_reference: str | None = None,
        finding: str | None = None,
    ) -> dict:
        # MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- provenance/
        # source_reference/finding are additive, optional kwargs (default
        # 'MANUAL'/None/None, byte-identical to every pre-existing caller's
        # behavior) -- see pm_occurrence_repository.py's own identical
        # header note. `finding` was previously only settable via
        # update_draft; a historically-imported reading whose source
        # document carried a Finding must be able to persist it at
        # creation time too, since promotion is a single create_draft
        # call, never followed by an update_draft round-trip.
        code = _new_code()
        measurement_cols = ", ".join(_MEASUREMENT_COLUMNS)
        measurement_vals = ", ".join(_sql(measurements.get(col)) for col in _MEASUREMENT_COLUMNS)
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO condition_monitoring_reading "
                "(condition_monitoring_reading_code, condition_monitoring_schedule_code, "
                f"asset_code, asset_type, reading_date, {measurement_cols}, "
                "workflow_status, provenance, created_by, updated_by, source_reference, finding) VALUES "
                f"({_sql(code)}, {_sql(condition_monitoring_schedule_code)}, {_sql(asset_code)}, "
                f"{_sql(asset_type)}, {_sql(reading_date)}, {measurement_vals}, "
                f"{_sql(DRAFT)}, {_sql(provenance)}, {_sql(created_by)}, {_sql(created_by)}, "
                f"{_sql(source_reference)}, {_sql(finding)}) "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

    def update_draft(
        self,
        reading_code: str,
        *,
        reading_date: str | None,
        measurements: dict,
        finding: str | None,
        updated_by: str,
    ) -> dict | None:
        measurement_sets = ", ".join(f"{col} = {_sql(measurements.get(col))}" for col in _MEASUREMENT_COLUMNS)
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE condition_monitoring_reading SET "
                f"reading_date = {_sql(reading_date)}, "
                f"{measurement_sets}, "
                f"finding = {_sql(finding)}, "
                f"updated_by = {_sql(updated_by)}, updated_at = NOW() "
                f"WHERE condition_monitoring_reading_code = {_sql(reading_code)} "
                f"AND workflow_status IN {_EDITABLE_STATUSES_SQL} "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def submit(self, reading_code: str, *, submitted_by: str) -> dict | None:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE condition_monitoring_reading SET "
                "workflow_status = 'SUBMITTED', "
                f"submitted_by = {_sql(submitted_by)}, submitted_at = NOW(), "
                f"updated_by = {_sql(submitted_by)}, updated_at = NOW() "
                f"WHERE condition_monitoring_reading_code = {_sql(reading_code)} "
                f"AND workflow_status IN {_EDITABLE_STATUSES_SQL} "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def admin_return_for_correction(self, reading_code: str, *, reviewed_by: str, return_reason: str) -> dict | None:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE condition_monitoring_reading SET "
                "workflow_status = 'RETURNED_FOR_CORRECTION', "
                f"reviewed_by = {_sql(reviewed_by)}, reviewed_at = NOW(), "
                f"return_reason = {_sql(return_reason)}, "
                f"updated_by = {_sql(reviewed_by)}, updated_at = NOW() "
                f"WHERE condition_monitoring_reading_code = {_sql(reading_code)} AND workflow_status = 'SUBMITTED' "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def technical_return_for_correction(
        self, reading_code: str, *, technical_reviewed_by: str, technical_comment: str
    ) -> dict | None:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE condition_monitoring_reading SET "
                "workflow_status = 'RETURNED_FOR_CORRECTION', "
                f"technical_reviewed_by = {_sql(technical_reviewed_by)}, technical_reviewed_at = NOW(), "
                f"technical_comment = {_sql(technical_comment)}, "
                f"updated_by = {_sql(technical_reviewed_by)}, updated_at = NOW() "
                f"WHERE condition_monitoring_reading_code = {_sql(reading_code)} AND workflow_status = 'SUBMITTED' "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def technical_finalize(
        self,
        reading_code: str,
        *,
        technical_reviewed_by: str,
        technical_outcome: str,
        technical_comment: str | None,
        technical_recommendation: str | None,
    ) -> dict | None:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE condition_monitoring_reading SET "
                "workflow_status = 'FINALIZED', "
                f"technical_reviewed_by = {_sql(technical_reviewed_by)}, technical_reviewed_at = NOW(), "
                f"technical_outcome = {_sql(technical_outcome)}, "
                f"technical_comment = {_sql(technical_comment)}, "
                f"technical_recommendation = {_sql(technical_recommendation)}, "
                f"updated_by = {_sql(technical_reviewed_by)}, updated_at = NOW() "
                f"WHERE condition_monitoring_reading_code = {_sql(reading_code)} AND workflow_status = 'SUBMITTED' "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None


__all__ = ["ConditionMonitoringReadingRepository", "_MEASUREMENT_COLUMNS"]
