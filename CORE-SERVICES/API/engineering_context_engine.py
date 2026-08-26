from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from . import maintenance_intelligence_service as mis
from .cm_report_gateway import CMReportGateway
from .condition_monitoring_reading_gateway import ConditionMonitoringReadingGateway
from .maintenance_history_gateway import MaintenanceHistoryGateway
from .pm_occurrence_gateway import PMOccurrenceGateway
from .pm_schedule_gateway import PMScheduleGateway
from .pump_gateway import PumpGateway
from .seal_gateway import SealGateway
from .seal_pump_compatibility_gateway import SealPumpCompatibilityGateway
from .seal_stock_gateway import SealStockGateway
from .work_order_gateway import WorkOrderGateway

CONTEXT_VERSION = "1.0.0"

# Mirrors AI5R-STUDIO/dashboard/src/modules/ltsa/utils/pmMapping.js's
# DUE_SOON_WINDOW_DAYS -- ADR-PM-001: status ACTIVE/ON_HOLD are stored;
# DUE_SOON/OVERDUE are computed from next_due vs. today, never stored. No
# source document pins an exact window; 7 days is that migration's
# disclosed, adjustable assumption. This is the first backend (Python)
# implementation of that same rule -- kept numerically identical to the
# existing frontend rule rather than inventing a second, competing one.
PM_DUE_SOON_WINDOW_DAYS = 7

# CM Report's priority enum (ADR-CM-001: "same shape as work_order.priority,
# a disclosed overlap"). work_order.priority itself is an open string in
# its schema, so this ordering is reused here as the closest existing,
# documented precedent rather than inventing a new ranking.
WORK_ORDER_PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _coerce_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

OPEN_CM_REPORT_STATUSES = {"OPEN", "IN_PROGRESS"}
ABNORMAL_CM_SEVERITIES = {"MINOR", "MODERATE"}
CRITICAL_CM_SEVERITIES = {"MAJOR", "CRITICAL"}


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


class EngineeringContextEngine:
    """Gathers and normalizes Pump, History, PM, CM, Seal, Inventory, and
    Work Order data into a single canonical EngineeringContext object, per
    MWO-LTSA-ENGCTX-001. This is the first production AI component for
    LTSA -- it produces no recommendation and makes no LLM call; it only
    assembles deterministic engineering context.

    Reuse before create: every value this engine can obtain from
    maintenance_intelligence_service's existing wrappers is obtained from
    there unchanged (get_pump_last_pm, get_pump_last_cm,
    get_pump_condition_monitoring_flag, get_pump_spare_parts,
    get_active_work_orders, get_pump_history) -- this engine does not
    reimplement any of that filtering/sorting logic. Only PM Schedule
    status/next_due and CM Report open-status scanning have no existing
    MIS wrapper (confirmed by repository archaeology) and are gathered
    directly from PMScheduleGateway/CMReportGateway here, since MIS
    exposes no function for either today.
    """

    def __init__(
        self,
        pump_gateway: PumpGateway | None = None,
        maintenance_history_gateway: MaintenanceHistoryGateway | None = None,
        pm_occurrence_gateway: PMOccurrenceGateway | None = None,
        pm_schedule_gateway: PMScheduleGateway | None = None,
        cm_report_gateway: CMReportGateway | None = None,
        condition_monitoring_reading_gateway: ConditionMonitoringReadingGateway | None = None,
        seal_gateway: SealGateway | None = None,
        seal_stock_gateway: SealStockGateway | None = None,
        seal_pump_compatibility_gateway: SealPumpCompatibilityGateway | None = None,
        work_order_gateway: WorkOrderGateway | None = None,
        mechanical_seal_stock_repository: Any | None = None,
    ):
        self.pump_gateway = pump_gateway or PumpGateway()
        self.maintenance_history_gateway = maintenance_history_gateway or MaintenanceHistoryGateway()
        self.pm_occurrence_gateway = pm_occurrence_gateway or PMOccurrenceGateway()
        self.pm_schedule_gateway = pm_schedule_gateway or PMScheduleGateway()
        self.cm_report_gateway = cm_report_gateway or CMReportGateway()
        self.condition_monitoring_reading_gateway = (
            condition_monitoring_reading_gateway or ConditionMonitoringReadingGateway()
        )
        self.seal_gateway = seal_gateway or SealGateway()
        self.seal_stock_gateway = seal_stock_gateway or SealStockGateway()
        self.seal_pump_compatibility_gateway = (
            seal_pump_compatibility_gateway or SealPumpCompatibilityGateway()
        )
        self.work_order_gateway = work_order_gateway or WorkOrderGateway()
        self.mechanical_seal_stock_repository = mechanical_seal_stock_repository

    def build(self, tag_number: str, today: date | None = None) -> dict[str, Any]:
        today = today or date.today()

        asset = self._build_asset(tag_number)
        maintenance_summary = self._build_maintenance_summary(tag_number)
        pm_summary, pm_evidence = self._build_pm_summary(tag_number, today)
        cm_summary, cm_evidence = self._build_cm_summary(tag_number)
        seal_summary, spare_parts = self._build_seal_summary(tag_number)
        inventory_summary = self._build_inventory_summary(spare_parts)
        workorder_summary = self._build_workorder_summary(tag_number)

        evidence = pm_evidence + cm_evidence
        if seal_summary["stock_availability"] in {"LOW", "OUT"}:
            evidence.append(self._seal_low_stock_evidence(spare_parts, seal_summary["stock_availability"]))

        engineering_flags = [item["flag"] for item in evidence]

        return {
            "asset": asset,
            "maintenance_summary": maintenance_summary,
            "pm_summary": pm_summary,
            "cm_summary": cm_summary,
            "seal_summary": seal_summary,
            "inventory_summary": inventory_summary,
            "workorder_summary": workorder_summary,
            "engineering_flags": engineering_flags,
            "evidence": evidence,
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "asset_code": tag_number,
                "context_version": CONTEXT_VERSION,
            },
        }

    # -- Asset -----------------------------------------------------------

    def _build_asset(self, tag_number: str) -> dict[str, Any]:
        response = self.pump_gateway.get_pump(tag_number)
        data = (response.get("data") or {}) if response.get("success") else {}

        return {
            "tag_number": tag_number,
            "pump_name": data.get("pump_name"),
            "manufacturer": data.get("manufacturer"),
            "model": data.get("model"),
            "status": data.get("status"),
        }

    # -- History -----------------------------------------------------------

    def _build_maintenance_summary(self, tag_number: str) -> dict[str, Any]:
        history = mis.get_pump_history(tag_number, maintenance_history_gateway=self.maintenance_history_gateway)
        records = history.get("records") or []
        records_sorted = sorted(records, key=lambda record: record.get("performed_at") or "", reverse=True)

        last_5_events = [
            {
                "record_code": record.get("maintenance_record_code"),
                "performed_at": record.get("performed_at"),
                "performed_by": record.get("performed_by"),
                "work_order_code": record.get("work_order_code"),
            }
            for record in records_sorted[:5]
        ]

        work_order_types = self._work_order_type_map()
        breakdown_records = [
            record for record in records_sorted if work_order_types.get(record.get("work_order_code")) == "CM"
        ]
        latest_breakdown = None
        if breakdown_records:
            record = breakdown_records[0]
            latest_breakdown = {
                "record_code": record.get("maintenance_record_code"),
                "performed_at": record.get("performed_at"),
                "work_order_code": record.get("work_order_code"),
            }

        return {
            "event_count": len(records),
            "last_5_events": last_5_events,
            "latest_breakdown": latest_breakdown,
        }

    def _work_order_type_map(self) -> dict[str, str]:
        response = self.work_order_gateway.list_work_orders()
        return {
            wo.get("work_order_code"): wo.get("work_type")
            for wo in (response.get("data") or [])
        }

    # -- PM ----------------------------------------------------------------

    def _build_pm_summary(self, tag_number: str, today: date) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        last_pm_result = mis.get_pump_last_pm(
            tag_number,
            maintenance_history_gateway=self.maintenance_history_gateway,
            work_order_gateway=self.work_order_gateway,
            pm_occurrence_gateway=self.pm_occurrence_gateway,
        )
        last_pm = last_pm_result.get("last_pm")

        schedule_response = self.pm_schedule_gateway.list_pm_schedules()
        schedules = [
            record
            for record in (schedule_response.get("data") or [])
            if record.get("asset_code") == tag_number
        ]
        schedules_sorted = sorted(schedules, key=lambda record: record.get("next_due") or "")
        schedule = schedules_sorted[0] if schedules_sorted else None

        status = self._compute_pm_status(schedule, today)
        overdue = status == "OVERDUE"

        pm_summary = {"last_pm": last_pm, "status": status, "overdue": overdue}

        evidence: list[dict[str, Any]] = []
        if status == "OVERDUE":
            evidence.append(
                {"flag": "PM_OVERDUE", "source": "PMSchedule", "reference": schedule.get("pm_schedule_code")}
            )
        if schedule is None:
            evidence.append({"flag": "NO_ACTIVE_PM", "source": "PMSchedule", "reference": tag_number})

        return pm_summary, evidence

    @staticmethod
    def _compute_pm_status(schedule: dict[str, Any] | None, today: date) -> str:
        if schedule is None:
            return "UNSCHEDULED"

        stored_status = schedule.get("status")
        if stored_status != "ACTIVE":
            return stored_status or "UNSCHEDULED"

        next_due = _parse_date(schedule.get("next_due"))
        if next_due is None:
            return "ACTIVE"

        days_until_due = (next_due - today).days
        if days_until_due < 0:
            return "OVERDUE"
        if days_until_due <= PM_DUE_SOON_WINDOW_DAYS:
            return "DUE_SOON"
        return "ACTIVE"

    # -- CM ------------------------------------------------------------------

    def _build_cm_summary(self, tag_number: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        flag_result = mis.get_pump_condition_monitoring_flag(
            tag_number, condition_monitoring_reading_gateway=self.condition_monitoring_reading_gateway
        )
        leak_flag = bool(flag_result.get("flagged"))
        latest_flagged_reading = flag_result.get("latest_flagged_reading")

        latest_abnormal_values = None
        if leak_flag and latest_flagged_reading:
            latest_abnormal_values = {
                "reading_code": latest_flagged_reading.get("condition_monitoring_reading_code"),
                "reading_date": latest_flagged_reading.get("reading_date"),
                "mechanical_seal_leak_de": latest_flagged_reading.get("mechanical_seal_leak_de"),
                "mechanical_seal_leak_nde": latest_flagged_reading.get("mechanical_seal_leak_nde"),
            }

        reports_response = self.cm_report_gateway.list_cm_reports()
        reports = [
            record for record in (reports_response.get("data") or []) if record.get("asset_code") == tag_number
        ]
        open_reports = sorted(
            (record for record in reports if record.get("status") in OPEN_CM_REPORT_STATUSES),
            key=lambda record: record.get("created_at") or "",
            reverse=True,
        )
        open_report = open_reports[0] if open_reports else None

        overall_condition = "NORMAL"
        if open_report is not None and open_report.get("severity") in CRITICAL_CM_SEVERITIES:
            overall_condition = "CRITICAL"
        elif leak_flag or (
            open_report is not None and open_report.get("severity") in ABNORMAL_CM_SEVERITIES
        ):
            overall_condition = "ABNORMAL"

        cm_summary = {
            "latest_abnormal_values": latest_abnormal_values,
            "overall_condition": overall_condition,
            "leak_flag": leak_flag,
        }

        evidence: list[dict[str, Any]] = []
        if overall_condition in {"ABNORMAL", "CRITICAL"}:
            if leak_flag and latest_flagged_reading:
                evidence.append(
                    {
                        "flag": "CM_ABNORMAL",
                        "source": "ConditionMonitoringReading",
                        "reference": latest_flagged_reading.get("condition_monitoring_reading_code"),
                    }
                )
            elif open_report is not None:
                evidence.append(
                    {"flag": "CM_ABNORMAL", "source": "CMReport", "reference": open_report.get("cm_report_code")}
                )
        if open_report is not None:
            evidence.append(
                {"flag": "OPEN_BREAKDOWN", "source": "CMReport", "reference": open_report.get("cm_report_code")}
            )

        return cm_summary, evidence

    # -- Seal / Inventory ----------------------------------------------------

    def _build_seal_summary(self, tag_number: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        compatibility = self.seal_pump_compatibility_gateway.list_seal_pump_compatibilities()
        seal_codes = [
            record.get("seal_code")
            for record in (compatibility.get("data") or [])
            if record.get("pump_tag_number") == tag_number
        ]
        seals = self.seal_gateway.list_seals()
        seal_by_code = {record.get("seal_code"): record for record in (seals.get("data") or [])}
        stock_rows = (
            self.mechanical_seal_stock_repository.list_for_equipment(tag_number)
            if self.mechanical_seal_stock_repository is not None
            else []
        )
        spare_parts = [
            {
                "seal_code": row.get("seal_code") or row.get("stock_pool_id"),
                "part_name": row.get("seal_type") or (seal_by_code.get(row.get("seal_code")) or {}).get("seal_name"),
                "quantity_on_hand": row.get("quantity_on_hand"),
                "reorder_point": None,
                "location": row.get("stock_location"),
            }
            for row in stock_rows
        ]
        if not spare_parts:
            spare_parts = [
                {"seal_code": code, "part_name": (seal_by_code.get(code) or {}).get("seal_name"),
                 "quantity_on_hand": None, "reorder_point": None, "location": None}
                for code in seal_codes
            ]

        compatibility = [
            {"seal_code": part.get("seal_code"), "part_name": part.get("part_name")} for part in spare_parts
        ]

        stock_availability = self._aggregate_stock_availability(spare_parts)

        seal_summary = {
            # No data source distinguishes "the seal currently installed on
            # this pump" from "seals compatible with this pump type" --
            # always null, a disclosed gap rather than a fabricated fact
            # (the same "unknown vs. confirmed" discipline
            # get_pump_spare_parts already applies to stock rows).
            "installed_seal": None,
            "compatibility": compatibility,
            "stock_availability": stock_availability,
        }

        return seal_summary, spare_parts

    @staticmethod
    def _aggregate_stock_availability(spare_parts: list[dict[str, Any]]) -> str:
        if not spare_parts:
            return "UNKNOWN"

        statuses = set()
        for part in spare_parts:
            quantity = _coerce_number(part.get("quantity_on_hand"))
            reorder_point = _coerce_number(part.get("reorder_point"))
            if quantity is None:
                statuses.add("UNKNOWN")
            elif quantity <= 0:
                statuses.add("OUT")
            elif reorder_point is not None and quantity <= reorder_point:
                statuses.add("LOW")
            else:
                statuses.add("OK")

        for status in ("OUT", "LOW", "UNKNOWN", "OK"):
            if status in statuses:
                return status
        return "UNKNOWN"

    @staticmethod
    def _seal_low_stock_evidence(spare_parts: list[dict[str, Any]], worst_status: str) -> dict[str, Any]:
        target = "OUT" if worst_status == "OUT" else "LOW"
        for part in spare_parts:
            quantity = _coerce_number(part.get("quantity_on_hand"))
            reorder_point = _coerce_number(part.get("reorder_point"))
            if quantity is None:
                continue
            if target == "OUT" and quantity <= 0:
                return {"flag": "SEAL_LOW_STOCK", "source": "SealStock", "reference": part.get("seal_code")}
            if target == "LOW" and reorder_point is not None and 0 < quantity <= reorder_point:
                return {"flag": "SEAL_LOW_STOCK", "source": "SealStock", "reference": part.get("seal_code")}
        return {"flag": "SEAL_LOW_STOCK", "source": "SealStock", "reference": None}

    @staticmethod
    def _build_inventory_summary(spare_parts: list[dict[str, Any]]) -> dict[str, Any]:
        available = []
        missing_critical_parts = []
        for part in spare_parts:
            quantity = _coerce_number(part.get("quantity_on_hand"))
            seal_code = part.get("seal_code")
            if quantity is None or quantity <= 0:
                missing_critical_parts.append(seal_code)
            else:
                available.append(seal_code)

        return {"available": available, "missing_critical_parts": missing_critical_parts}

    # -- Work Orders -----------------------------------------------------------

    def _build_workorder_summary(self, tag_number: str) -> dict[str, Any]:
        result = mis.get_active_work_orders(tag_number, work_order_gateway=self.work_order_gateway)
        work_orders = result.get("work_orders") or []

        highest_priority = None
        if work_orders:
            ranked = sorted(
                work_orders,
                key=lambda wo: WORK_ORDER_PRIORITY_ORDER.get(wo.get("priority"), len(WORK_ORDER_PRIORITY_ORDER)),
            )
            highest_priority = ranked[0].get("priority")

        newest_work_order = None
        if work_orders:
            # No creation timestamp exists on work_order (confirmed by
            # schema archaeology) -- due_date is the only orderable date
            # field available. "Newest" is therefore a disclosed proxy:
            # the open work order with the furthest-out due_date, not a
            # true creation-order ranking.
            newest = sorted(work_orders, key=lambda wo: wo.get("due_date") or "", reverse=True)[0]
            newest_work_order = {
                "work_order_code": newest.get("work_order_code"),
                "work_type": newest.get("work_type"),
                "priority": newest.get("priority"),
                "status": newest.get("status"),
                "due_date": newest.get("due_date"),
            }

        return {
            "open_count": len(work_orders),
            "highest_priority": highest_priority,
            "newest_work_order": newest_work_order,
        }
