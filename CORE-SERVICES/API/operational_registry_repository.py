from __future__ import annotations

import sys
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


class PMScheduleRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def list_pm_schedules(self, *, scope: frozenset[str] | None = None) -> dict:
        rows = _json_query(
            "SELECT p.pm_schedule_code, p.asset_code, p.asset_type, p.procedure, p.frequency, "
            "p.trigger_type, p.checklist, p.assigned_to, p.estimated_duration_hours, p.next_due, "
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
            "p.trigger_type, p.checklist, p.assigned_to, p.estimated_duration_hours, p.next_due, "
            "p.last_performed, p.status, p.created_at, p.updated_at, pump.area, pump.name AS pump_name "
            "FROM public.pm_schedule p LEFT JOIN public.ltsa_pumps pump ON pump.tag_number = p.asset_code "
            f"WHERE p.pm_schedule_code = {_sql(code)} AND p.deleted_at IS NULL {_scope_and('pump.area', scope)}",
            self._runner,
        )
        return _detail("PM schedule not found", rows[0] if rows else None)

    def create(self, *, values: dict, actor: str) -> dict | None:
        fields = ("pm_schedule_code", "asset_code", "asset_type", "procedure", "frequency", "trigger_type", "interval_unit", "effective_date", "next_due", "assigned_to", "provenance", "source_reference")
        vals = ", ".join(_sql(values.get(field)) for field in fields)
        rows = _json_query(
            "WITH ins AS (INSERT INTO public.pm_schedule (" + ",".join(fields) + ", created_by, updated_by) "
            "SELECT " + vals + ", " + _sql(actor) + ", " + _sql(actor) + " WHERE EXISTS (SELECT 1 FROM public.ltsa_pumps WHERE tag_number = " + _sql(values.get("asset_code")) + ") RETURNING *), audit AS (INSERT INTO record_change_history (entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) SELECT 'PM_SCHEDULE', pm_schedule_code, '__record__', NULL, row_to_json(ins)::text, " + _sql(actor) + ", 'CREATE' FROM ins) SELECT * FROM ins",
            self._runner,
        )
        return rows[0] if rows else None

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
            "s.applicable_parameters, s.created_at, s.updated_at, pump.area, pump.name AS pump_name "
            "FROM public.condition_monitoring_schedule s "
            "LEFT JOIN public.ltsa_pumps pump ON pump.tag_number = s.asset_code "
            "WHERE s.deleted_at IS NULL "
            f"AND {_scope_and('pump.area', scope)[4:] if _scope_and('pump.area', scope) else 'TRUE'} "
            "ORDER BY s.condition_monitoring_schedule_code ASC",
            self._runner,
        )
        return _response("Condition Monitoring schedule list retrieved", rows)

    def get_condition_monitoring_schedule(self, code: str, *, scope: frozenset[str] | None = None) -> dict:
        rows = _json_query(
            "SELECT s.condition_monitoring_schedule_code, s.asset_code, s.asset_type, s.frequency, "
            "s.applicable_parameters, s.created_at, s.updated_at, pump.area, pump.name AS pump_name "
            "FROM public.condition_monitoring_schedule s "
            "LEFT JOIN public.ltsa_pumps pump ON pump.tag_number = s.asset_code "
            f"WHERE s.condition_monitoring_schedule_code = {_sql(code)} AND s.deleted_at IS NULL {_scope_and('pump.area', scope)}",
            self._runner,
        )
        return _detail("Condition Monitoring schedule not found", rows[0] if rows else None)

    def create(self, *, values: dict, actor: str) -> dict | None:
        fields = ("condition_monitoring_schedule_code", "asset_code", "asset_type", "monitoring_type", "measurement_point", "frequency", "interval_unit", "effective_date", "provenance", "source_reference")
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
