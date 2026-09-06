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

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


def _response(message: str, rows: list[dict]) -> dict:
    return {"success": True, "message": message, "count": len(rows), "data": rows, "items": rows}


def _detail(message: str, row: dict | None) -> dict:
    return {"success": row is not None, "message": "found" if row is not None else message, "data": row}


def _scope_where(column: str, scope: frozenset[str] | None) -> str:
    if scope is None:
        return ""
    if not scope:
        return "WHERE FALSE"
    values = ", ".join(_sql(area) for area in sorted(scope))
    return f"WHERE {column} IN ({values})"


def _scope_and(column: str, scope: frozenset[str] | None) -> str:
    where = _scope_where(column, scope)
    return "" if not where else "AND " + where.removeprefix("WHERE ")


def _pm_schedule_code_exists(runner: "DatabaseRunner", code: str) -> bool:
    rows = _json_query(
        f"SELECT 1 AS present FROM public.pm_schedule WHERE pm_schedule_code = {_sql(code)}",
        runner,
    )
    return bool(rows)


class BulkPMScheduleValidationError(ValueError):
    # AI5R-PHASE4E3 -- carries a client_row_id -> message map so the
    # router/frontend can surface a human-readable error against the
    # exact row that failed (Section G: "Display human-readable row
    # errors. Never: [object Object]"), instead of a single flattened
    # exception string.
    def __init__(self, row_errors: dict[str, str]) -> None:
        self.row_errors = row_errors
        super().__init__(f"{len(row_errors)} row(s) failed bulk validation")


def _new_pm_schedule_code(runner: "DatabaseRunner", *, max_attempts: int = 5) -> str:
    # AI5R-PHASE4E1 -- OWNER DECISIONS 1-3: schedule code is system-
    # generated, never typed by a human, format PMSCH-{12 uppercase hex},
    # mirroring pm_occurrence_repository.py's own _new_code() pattern.
    # 12 hex chars (48 bits) makes a real collision practically
    # impossible, but pm_schedule_code is the table's PRIMARY KEY, so a
    # silent collision would corrupt an existing schedule -- checked
    # explicitly (including soft-deleted rows, since the PK constraint
    # does not exempt them) and retried a bounded number of times rather
    # than trusted blindly.
    for _ in range(max_attempts):
        candidate = f"PMSCH-{uuid.uuid4().hex[:12].upper()}"
        if not _pm_schedule_code_exists(runner, candidate):
            return candidate
    raise RuntimeError("could not generate a unique pm_schedule_code after repeated attempts")


class PMScheduleRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def list_pm_schedules(self, *, scope: frozenset[str] | None = None) -> dict:
        rows = _json_query(
            "SELECT p.pm_schedule_code, p.asset_code, p.asset_type, p.procedure, p.frequency, "
            "p.trigger_type, p.checklist, p.planned_activities, p.assigned_to, p.estimated_duration_hours, p.next_due, "
            "p.last_performed, p.status, p.created_at, p.updated_at, pump.area, pump.name AS pump_name "
            "FROM public.pm_schedule p LEFT JOIN public.ltsa_pumps pump ON pump.tag_number = p.asset_code "
            "WHERE p.deleted_at IS NULL "
            f"{_scope_and('pump.area', scope)} "
            "ORDER BY p.next_due ASC NULLS LAST, p.pm_schedule_code ASC",
            self._runner,
        )
        return _response("PM schedules listed", rows)

    def get_pm_schedule(self, code: str, *, scope: frozenset[str] | None = None) -> dict:
        rows = _json_query(
            "SELECT p.pm_schedule_code, p.asset_code, p.asset_type, p.procedure, p.frequency, "
            "p.trigger_type, p.checklist, p.planned_activities, p.assigned_to, p.estimated_duration_hours, p.next_due, "
            "p.last_performed, p.status, p.created_at, p.updated_at, pump.area, pump.name AS pump_name "
            "FROM public.pm_schedule p LEFT JOIN public.ltsa_pumps pump ON pump.tag_number = p.asset_code "
            f"WHERE p.pm_schedule_code = {_sql(code)} AND p.deleted_at IS NULL {_scope_and('pump.area', scope)}",
            self._runner,
        )
        return _detail("PM schedule not found", rows[0] if rows else None)

    def create(self, *, values: dict, actor: str) -> dict | None:
        # AI5R-PHASE4E1 -- Section B: caller does not need to supply
        # pm_schedule_code; when omitted (the new UI never sends one), the
        # backend generates it. A caller that DOES pass one (e.g. a future
        # historical-import path) keeps working unchanged -- existing
        # codes/FK/reference behavior is untouched.
        code = values.get("pm_schedule_code") or _new_pm_schedule_code(self._runner)
        # Section D: planned_activities is PLANNED work only, stored as
        # its own JSONB column, never written into pm_occurrence.activities
        # and never carrying a `done` flag -- kept fully separate from the
        # PERFORMED-activities contract pm_occurrence_repository.py owns.
        planned_activities = values.get("planned_activities")

        fields = (
            "pm_schedule_code", "asset_code", "asset_type", "procedure", "frequency", "trigger_type",
            "interval_unit", "effective_date", "next_due", "assigned_to", "estimated_duration_hours",
            "provenance", "source_reference", "planned_activities",
        )

        def _value_sql(field: str) -> str:
            if field == "pm_schedule_code":
                return _sql(code)
            if field == "planned_activities":
                return f"{_sql(json.dumps(planned_activities) if planned_activities is not None else None)}::jsonb"
            return _sql(values.get(field))

        vals = ", ".join(_value_sql(field) for field in fields)
        rows = _json_query(
            "WITH ins AS (INSERT INTO public.pm_schedule (" + ",".join(fields) + ", created_by, updated_by) "
            "SELECT " + vals + ", " + _sql(actor) + ", " + _sql(actor) + " WHERE EXISTS (SELECT 1 FROM public.ltsa_pumps WHERE tag_number = " + _sql(values.get("asset_code")) + ") RETURNING *), audit AS (INSERT INTO record_change_history (entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) SELECT 'PM_SCHEDULE', pm_schedule_code, '__record__', NULL, row_to_json(ins)::text, " + _sql(actor) + ", 'CREATE' FROM ins) SELECT * FROM ins",
            self._runner,
        )
        return rows[0] if rows else None

    def bulk_create(self, *, rows: list[dict], actor: str) -> list[dict]:
        # AI5R-PHASE4E3, Section I -- ONE atomic backend bulk endpoint.
        # Server-side revalidation happens HERE, independent of whatever
        # the frontend already checked (Section K: "Do not trust frontend
        # validation"): every row's asset_code is checked against the
        # canonical pump master and the batch is checked for internal
        # duplicates BEFORE any SQL INSERT is built or executed. On any
        # row error, raises BulkPMScheduleValidationError and creates
        # NOTHING -- Section M's own "9 valid, 1 invalid -> 0 created"
        # requirement holds because the INSERT is never even attempted in
        # that case, not because of a transaction rollback.
        if not rows:
            return []

        asset_codes = sorted({row["asset_code"] for row in rows})
        existing = _json_query(
            "SELECT tag_number FROM public.ltsa_pumps WHERE tag_number IN ("
            + ", ".join(_sql(code) for code in asset_codes)
            + ")",
            self._runner,
        )
        canonical_pumps = {r["tag_number"] for r in existing}

        row_errors: dict[str, str] = {}
        seen_keys: dict[tuple, str] = {}
        for row in rows:
            client_row_id = row["client_row_id"]
            if row["asset_code"] not in canonical_pumps:
                row_errors[client_row_id] = f"Unknown pump: {row['asset_code']}"
                continue
            dup_key = (row["asset_code"], row["frequency"], row.get("effective_date"))
            if dup_key in seen_keys:
                row_errors[client_row_id] = (
                    f"Duplicate of row {seen_keys[dup_key]!r}: same pump + frequency + start date in this batch"
                )
                continue
            seen_keys[dup_key] = client_row_id

        if row_errors:
            raise BulkPMScheduleValidationError(row_errors)

        # Codes are generated (and collision-checked, including against
        # each other within this same batch) entirely in Python BEFORE the
        # INSERT is built, so the final result can be correlated back to
        # each row by simple positional zip -- no reliance on a multi-row
        # INSERT's RETURNING order, which Postgres does not formally
        # guarantee to match VALUES order.
        codes = self._new_pm_schedule_codes(len(rows))

        fields = (
            "pm_schedule_code", "asset_code", "asset_type", "procedure", "frequency", "trigger_type",
            "interval_unit", "effective_date", "next_due", "assigned_to", "estimated_duration_hours",
            "provenance", "source_reference", "planned_activities",
        )

        def _row_value_sql(row: dict, code: str, field: str) -> str:
            if field == "pm_schedule_code":
                return _sql(code)
            if field == "planned_activities":
                planned = row.get("planned_activities")
                return f"{_sql(json.dumps(planned) if planned is not None else None)}::jsonb"
            return _sql(row.get(field))

        value_tuples = []
        for row, code in zip(rows, codes):
            value_tuples.append(
                "(" + ", ".join(_row_value_sql(row, code, field) for field in fields)
                + f", {_sql(actor)}, {_sql(actor)})"
            )

        rows_created = _json_query(
            "WITH ins AS (INSERT INTO public.pm_schedule (" + ",".join(fields) + ", created_by, updated_by) "
            "VALUES " + ", ".join(value_tuples) + " RETURNING *), "
            "audit AS (INSERT INTO record_change_history (entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
            "SELECT 'PM_SCHEDULE', pm_schedule_code, '__record__', NULL, row_to_json(ins)::text, "
            + _sql(actor) + ", 'CREATE' FROM ins) "
            "SELECT * FROM ins",
            self._runner,
        )
        # A single INSERT...VALUES statement is one atomic unit of work in
        # Postgres regardless of the runner's autocommit setting -- either
        # every row above lands (len(rows_created) == len(rows)) or the
        # whole statement raises and NOTHING is created. This assertion is
        # a belt-and-suspenders sanity check, not the atomicity mechanism
        # itself.
        if len(rows_created) != len(rows):
            raise RuntimeError(
                f"bulk pm_schedule insert returned {len(rows_created)} rows, expected {len(rows)}"
            )

        return [{"client_row_id": row["client_row_id"], "pm_schedule_code": code} for row, code in zip(rows, codes)]

    def _new_pm_schedule_codes(self, count: int, *, max_attempts_per_code: int = 5) -> list[str]:
        codes: list[str] = []
        for _ in range(count):
            for _ in range(max_attempts_per_code):
                candidate = f"PMSCH-{uuid.uuid4().hex[:12].upper()}"
                if candidate not in codes and not _pm_schedule_code_exists(self._runner, candidate):
                    codes.append(candidate)
                    break
            else:
                raise RuntimeError("could not generate a unique pm_schedule_code after repeated attempts")
        return codes

    def update(self, code: str, *, values: dict, actor: str) -> dict | None:
        assignments = ", ".join(f"{field} = {_sql(value)}" for field, value in values.items() if value is not None)
        if not assignments:
            return self.get_pm_schedule(code).get("data")
        rows = _json_query(
            "WITH old AS (SELECT row_to_json(p)::text AS snapshot FROM public.pm_schedule p WHERE pm_schedule_code = " + _sql(code) + " AND deleted_at IS NULL), upd AS (UPDATE public.pm_schedule SET " + assignments + ", updated_by = " + _sql(actor) + ", updated_at = NOW() WHERE pm_schedule_code = " + _sql(code) + " AND deleted_at IS NULL RETURNING *), audit AS (INSERT INTO record_change_history (entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) SELECT 'PM_SCHEDULE', pm_schedule_code, '__record__', old.snapshot, row_to_json(upd)::text, " + _sql(actor) + ", 'UPDATE' FROM upd CROSS JOIN old) SELECT * FROM upd",
            self._runner,
        )
        return rows[0] if rows else None

    def soft_delete(self, code: str, *, actor: str) -> dict | None:
        rows = _json_query(
            "WITH old AS (SELECT row_to_json(p)::text AS snapshot FROM public.pm_schedule p WHERE pm_schedule_code = " + _sql(code) + " AND deleted_at IS NULL), upd AS (UPDATE public.pm_schedule SET deleted_at = NOW(), deleted_by = " + _sql(actor) + ", updated_by = " + _sql(actor) + ", updated_at = NOW() WHERE pm_schedule_code = " + _sql(code) + " AND deleted_at IS NULL RETURNING *), audit AS (INSERT INTO record_change_history (entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) SELECT 'PM_SCHEDULE', pm_schedule_code, '__record__', old.snapshot, NULL, " + _sql(actor) + ", 'DELETE' FROM upd CROSS JOIN old) SELECT * FROM upd",
            self._runner,
        )
        return rows[0] if rows else None


class CMReportRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def list_cm_reports(self, *, scope: frozenset[str] | None = None) -> dict:
        rows = _json_query(
            "SELECT c.cm_report_code, c.asset_code, c.asset_type, c.work_order_code, c.failure_category, "
            "c.severity, c.priority, c.failure_description, c.root_cause, c.immediate_action, "
            "c.corrective_action, c.downtime_hours, c.assigned_to, c.status, c.created_at, c.updated_at, "
            "c.source_workbook_name, c.source_sheet_name, c.source_row_number, c.failure_date, "
            "pump.area, pump.name AS pump_name "
            "FROM public.cm_report c LEFT JOIN public.ltsa_pumps pump ON pump.tag_number = c.asset_code "
            f"{_scope_where('pump.area', scope)} "
            "ORDER BY COALESCE(c.failure_date, c.created_at) DESC NULLS LAST, c.cm_report_code ASC",
            self._runner,
        )
        return _response("CM report list retrieved", rows)

    def get_cm_report(self, code: str, *, scope: frozenset[str] | None = None) -> dict:
        rows = _json_query(
            "SELECT c.cm_report_code, c.asset_code, c.asset_type, c.work_order_code, c.failure_category, "
            "c.severity, c.priority, c.failure_description, c.root_cause, c.immediate_action, "
            "c.corrective_action, c.downtime_hours, c.assigned_to, c.status, c.created_at, c.updated_at, "
            "c.source_workbook_name, c.source_sheet_name, c.source_row_number, c.failure_date, "
            "pump.area, pump.name AS pump_name "
            "FROM public.cm_report c LEFT JOIN public.ltsa_pumps pump ON pump.tag_number = c.asset_code "
            f"WHERE c.cm_report_code = {_sql(code)} {_scope_and('pump.area', scope)}",
            self._runner,
        )
        return _detail("CM report not found", rows[0] if rows else None)


class ConditionMonitoringScheduleRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def list_condition_monitoring_schedules(self, *, scope: frozenset[str] | None = None) -> dict:
        rows = _json_query(
            "SELECT s.condition_monitoring_schedule_code, s.asset_code, s.asset_type, s.frequency, "
            "s.applicable_parameters, s.status, s.next_due, s.created_at, s.updated_at, pump.area, pump.name AS pump_name "
            "FROM public.condition_monitoring_schedule s "
            "LEFT JOIN public.ltsa_pumps pump ON pump.tag_number = s.asset_code "
            "WHERE s.deleted_at IS NULL "
            f"AND {_scope_and('pump.area', scope)[4:] if _scope_and('pump.area', scope) else 'TRUE'} "
            "ORDER BY s.next_due ASC NULLS LAST, s.condition_monitoring_schedule_code ASC",
            self._runner,
        )
        return _response("Condition Monitoring schedule list retrieved", rows)

    def get_condition_monitoring_schedule(self, code: str, *, scope: frozenset[str] | None = None) -> dict:
        rows = _json_query(
            "SELECT s.condition_monitoring_schedule_code, s.asset_code, s.asset_type, s.frequency, "
            "s.applicable_parameters, s.status, s.next_due, s.created_at, s.updated_at, pump.area, pump.name AS pump_name "
            "FROM public.condition_monitoring_schedule s "
            "LEFT JOIN public.ltsa_pumps pump ON pump.tag_number = s.asset_code "
            f"WHERE s.condition_monitoring_schedule_code = {_sql(code)} AND s.deleted_at IS NULL {_scope_and('pump.area', scope)}",
            self._runner,
        )
        return _detail("Condition Monitoring schedule not found", rows[0] if rows else None)

    def create(self, *, values: dict, actor: str) -> dict | None:
        # MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- next_due added,
        # mirroring pm_schedule's own create() field list exactly. status
        # is deliberately NOT in this list: it always starts at the
        # column's own DEFAULT 'PLANNED' (migration 029) on create, the
        # same "never let a client dictate the starting lifecycle state"
        # choice pm_schedule's own create() already makes (status isn't in
        # its fields tuple either).
        fields = ("condition_monitoring_schedule_code", "asset_code", "asset_type", "monitoring_type", "measurement_point", "frequency", "interval_unit", "effective_date", "next_due", "provenance", "source_reference")
        rows = _json_query(
            "WITH ins AS (INSERT INTO public.condition_monitoring_schedule (" + ",".join(fields) + ", created_by, updated_by) SELECT " + ", ".join(_sql(values.get(field)) for field in fields) + ", " + _sql(actor) + ", " + _sql(actor) + " WHERE EXISTS (SELECT 1 FROM public.ltsa_pumps WHERE tag_number = " + _sql(values.get("asset_code")) + ") RETURNING *), audit AS (INSERT INTO record_change_history (entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) SELECT 'CONDITION_MONITORING_SCHEDULE', condition_monitoring_schedule_code, '__record__', NULL, row_to_json(ins)::text, " + _sql(actor) + ", 'CREATE' FROM ins) SELECT * FROM ins",
            self._runner,
        )
        return rows[0] if rows else None

    def update(self, code: str, *, values: dict, actor: str) -> dict | None:
        assignments = ", ".join(f"{field} = {_sql(value)}" for field, value in values.items() if value is not None)
        if not assignments:
            return self.get_condition_monitoring_schedule(code).get("data")
        rows = _json_query(
            "WITH old AS (SELECT row_to_json(s)::text AS snapshot FROM public.condition_monitoring_schedule s WHERE condition_monitoring_schedule_code = " + _sql(code) + " AND deleted_at IS NULL), upd AS (UPDATE public.condition_monitoring_schedule SET " + assignments + ", updated_by = " + _sql(actor) + ", updated_at = NOW() WHERE condition_monitoring_schedule_code = " + _sql(code) + " AND deleted_at IS NULL RETURNING *), audit AS (INSERT INTO record_change_history (entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) SELECT 'CONDITION_MONITORING_SCHEDULE', condition_monitoring_schedule_code, '__record__', old.snapshot, row_to_json(upd)::text, " + _sql(actor) + ", 'UPDATE' FROM upd CROSS JOIN old) SELECT * FROM upd",
            self._runner,
        )
        return rows[0] if rows else None

    def soft_delete(self, code: str, *, actor: str) -> dict | None:
        rows = _json_query(
            "WITH old AS (SELECT row_to_json(s)::text AS snapshot FROM public.condition_monitoring_schedule s WHERE condition_monitoring_schedule_code = " + _sql(code) + " AND deleted_at IS NULL), upd AS (UPDATE public.condition_monitoring_schedule SET deleted_at = NOW(), deleted_by = " + _sql(actor) + ", updated_by = " + _sql(actor) + ", updated_at = NOW() WHERE condition_monitoring_schedule_code = " + _sql(code) + " AND deleted_at IS NULL RETURNING *), audit AS (INSERT INTO record_change_history (entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) SELECT 'CONDITION_MONITORING_SCHEDULE', condition_monitoring_schedule_code, '__record__', old.snapshot, NULL, " + _sql(actor) + ", 'DELETE' FROM upd CROSS JOIN old) SELECT * FROM upd",
            self._runner,
        )
        return rows[0] if rows else None
