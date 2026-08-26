from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .cm_report_gateway import CMReportGateway
from .condition_monitoring_reading_gateway import ConditionMonitoringReadingGateway
from .maintenance_command_center import get_maintenance_command_center
from .maintenance_history_gateway import MaintenanceHistoryGateway
from .pm_occurrence_gateway import PMOccurrenceGateway
from .pump_gateway import PumpGateway
from .role_manufacturing import retrieve_role_artifact
from .seal_gateway import SealGateway
from .seal_pump_compatibility_gateway import SealPumpCompatibilityGateway
from .seal_stock_gateway import SealStockGateway
from .work_order_gateway import WorkOrderGateway

# ADR-ASSET360-001 Open Question 3: no source document evidences a
# specific recency window for "recent" Condition Monitoring activity.
# 30 days is a disclosed, adjustable default (roughly four weekly cycles,
# per the real report's own "1 x seminggu" cadence) -- not a fabricated
# business rule, the same discipline ADR-PM-001 applied to its 7-day
# DUE_SOON window.
DEFAULT_CONDITION_MONITORING_WINDOW_DAYS = 30

DEFAULT_ROOT_PATH = Path(__file__).resolve().parents[2]


def get_pump_status(
    tag_number: str,
    pump_gateway: PumpGateway | None = None,
) -> dict[str, Any]:
    """Show Pump Status: the pump's current detail, unchanged, via Pump
    Gateway."""

    pump_gateway = pump_gateway or PumpGateway()

    return pump_gateway.get_pump(tag_number)


def get_pump_history(
    tag_number: str,
    maintenance_history_gateway: MaintenanceHistoryGateway | None = None,
) -> dict[str, Any]:
    """Show Pump History: maintenance history records for one pump,
    filtered from Maintenance History Gateway's existing list."""

    maintenance_history_gateway = maintenance_history_gateway or MaintenanceHistoryGateway()
    response = maintenance_history_gateway.list_maintenance_history()
    records = [
        record
        for record in (response.get("data") or [])
        if record.get("asset_code") == tag_number
    ]

    return {
        "success": response.get("success", False),
        "tag_number": tag_number,
        "records": records,
    }


def get_pump_last_pm(
    tag_number: str,
    maintenance_history_gateway: MaintenanceHistoryGateway | None = None,
    work_order_gateway: WorkOrderGateway | None = None,
    pm_occurrence_gateway: PMOccurrenceGateway | None = None,
) -> dict[str, Any]:
    """Show Last PM: the most recent PM activity for this pump, per
    ADR-PM-OCCURRENCE-001 (MWO-MAINTINT-001) -- updated from
    ADR-PUMP-002's original, now-superseded assumption that a
    maintenance_history record linked to a work_type == 'PM' Work Order
    is the only source of PM activity.

    Considers two independent candidates and returns whichever is more
    recent, never silently preferring one:
      - "work_order": a maintenance_history record whose linked Work
        Order has work_type == 'PM' -- ADR-PUMP-002's original source,
        still valid for formally dispatched PM work, but no longer
        assumed to be the only source (ADR-PM-OCCURRENCE-001's Reason
        section).
      - "pm_occurrence": the most recent pm_occurrence row for this
        asset -- the canonical source for a PM Schedule's routine,
        evidenced-typical completion history (ADR-PM-OCCURRENCE-001).

    The winning candidate's origin is disclosed via `source` rather than
    merged into one indistinguishable record, the same "disclosed
    overlap, not merge" discipline ADR-CM-001 established. `performed_at`
    is normalized onto the wrapper regardless of source, so existing
    consumers (e.g. pumpMapping.js's `result?.last_pm?.performed_at`)
    keep working unchanged.
    """

    history = get_pump_history(tag_number, maintenance_history_gateway=maintenance_history_gateway)
    records = history.get("records") or []

    work_order_gateway = work_order_gateway or WorkOrderGateway()
    work_orders_response = work_order_gateway.list_work_orders()
    work_order_types = {
        wo.get("work_order_code"): wo.get("work_type")
        for wo in (work_orders_response.get("data") or [])
    }

    wo_pm_records = [
        record for record in records if work_order_types.get(record.get("work_order_code")) == "PM"
    ]
    wo_pm_sorted = sorted(wo_pm_records, key=lambda record: record.get("performed_at") or "", reverse=True)
    wo_latest = wo_pm_sorted[0] if wo_pm_sorted else None

    pm_occurrence_gateway = pm_occurrence_gateway or PMOccurrenceGateway()
    occurrences_response = pm_occurrence_gateway.list_pm_occurrences()
    occurrences = [
        occurrence
        for occurrence in (occurrences_response.get("data") or [])
        if occurrence.get("asset_code") == tag_number
    ]
    occurrences_sorted = sorted(
        occurrences, key=lambda occurrence: occurrence.get("occurrence_date") or "", reverse=True
    )
    occurrence_latest = occurrences_sorted[0] if occurrences_sorted else None

    candidates = []
    if wo_latest is not None:
        candidates.append(
            {"source": "work_order", "performed_at": wo_latest.get("performed_at"), "record": wo_latest}
        )
    if occurrence_latest is not None:
        candidates.append(
            {
                "source": "pm_occurrence",
                "performed_at": occurrence_latest.get("occurrence_date"),
                "record": occurrence_latest,
            }
        )

    candidates_sorted = sorted(candidates, key=lambda candidate: candidate["performed_at"] or "", reverse=True)

    return {
        # Best-effort: true if either source's underlying fetch succeeded,
        # not both -- one gateway being unavailable should not hide a
        # result the other gateway can still honestly provide.
        "success": history.get("success", False) or occurrences_response.get("success", False),
        "tag_number": tag_number,
        "last_pm": candidates_sorted[0] if candidates_sorted else None,
    }


def get_pump_last_cm(
    tag_number: str,
    cm_report_gateway: CMReportGateway | None = None,
) -> dict[str, Any]:
    """Show Last CM: the most recent cm_report for this pump, per
    ADR-ASSET360-001. Simpler than get_pump_last_pm's shape: cm_report is
    the sole source, with no work_order-linked comparison, since
    ADR-CM-001 already established cm_report as Corrective Maintenance's
    own canonical record, independent of whether a Work Order exists for
    a given incident.

    Sorted by `created_at` -- cm_report has no dedicated
    "occurred_at"/"reported_at" field, so this is a disclosed judgment
    call (the closest available proxy for "when this report was filed"),
    not an assumption presented as fact.
    """

    cm_report_gateway = cm_report_gateway or CMReportGateway()
    response = cm_report_gateway.list_cm_reports()
    records = [
        record for record in (response.get("data") or []) if record.get("asset_code") == tag_number
    ]
    records_sorted = sorted(records, key=lambda record: record.get("created_at") or "", reverse=True)

    return {
        "success": response.get("success", False),
        "tag_number": tag_number,
        "last_cm": records_sorted[0] if records_sorted else None,
    }


def get_pump_condition_monitoring_flag(
    tag_number: str,
    condition_monitoring_reading_gateway: ConditionMonitoringReadingGateway | None = None,
    window_days: int = DEFAULT_CONDITION_MONITORING_WINDOW_DAYS,
    today: date | None = None,
) -> dict[str, Any]:
    """Show Condition Monitoring Flag: whether any condition_monitoring_reading
    for this pump within the last `window_days` recorded a mechanical seal
    leak (DE or NDE side), per ADR-ASSET360-001. A new, previously
    impossible derivation -- Condition Monitoring had no canonical backend
    representation until ADR-CONDITION-MONITORING-001/WO-CMON-001.

    Never fabricates a threshold beyond the disclosed default window
    (see DEFAULT_CONDITION_MONITORING_WINDOW_DAYS) -- readings with no
    parseable `reading_date` are excluded from the window rather than
    assumed recent or assumed stale.
    """

    condition_monitoring_reading_gateway = (
        condition_monitoring_reading_gateway or ConditionMonitoringReadingGateway()
    )
    response = condition_monitoring_reading_gateway.list_condition_monitoring_readings()
    readings = [
        reading
        for reading in (response.get("data") or [])
        if reading.get("asset_code") == tag_number
    ]

    today = today or date.today()
    cutoff = today - timedelta(days=window_days)

    def _within_window(reading: dict[str, Any]) -> bool:
        raw_date = reading.get("reading_date")
        if not raw_date:
            return False
        try:
            parsed = date.fromisoformat(str(raw_date)[:10])
        except ValueError:
            return False
        return parsed >= cutoff

    recent_readings = [reading for reading in readings if _within_window(reading)]
    flagged_readings = [
        reading
        for reading in recent_readings
        if reading.get("mechanical_seal_leak_de") is True or reading.get("mechanical_seal_leak_nde") is True
    ]
    flagged_sorted = sorted(
        flagged_readings, key=lambda reading: reading.get("reading_date") or "", reverse=True
    )

    return {
        "success": response.get("success", False),
        "tag_number": tag_number,
        "flagged": len(flagged_readings) > 0,
        "window_days": window_days,
        "latest_flagged_reading": flagged_sorted[0] if flagged_sorted else None,
    }


def get_pump_spare_parts(
    tag_number: str,
    seal_pump_compatibility_gateway: SealPumpCompatibilityGateway | None = None,
    seal_stock_gateway: SealStockGateway | None = None,
    seal_gateway: SealGateway | None = None,
) -> dict[str, Any]:
    """Show Spare Parts: mechanical seals compatible with this pump, with
    their current stock context, per the Inventory Context Experience
    (MWO-INV-CTX-001). Sourced entirely from the existing Seal domain
    (seal_pump_compatibility, seal_stock, seal_registry -- MWO-LTSA-030,
    previously schema-only with no gateway/route layer): filter
    seal_pump_compatibility to this pump's tag_number first, the same
    "filter first" approach get_pump_history already uses for
    maintenance_history, then join each compatible seal_code against
    seal_stock and seal_registry.

    Engineering context only, not warehouse management: read-only, and a
    compatible seal with no seal_stock row is listed with
    quantity_on_hand/reorder_point/location left null rather than
    fabricated as zero -- "no stock record" and "confirmed zero stock"
    are not the same fact.
    """

    seal_pump_compatibility_gateway = seal_pump_compatibility_gateway or SealPumpCompatibilityGateway()
    compatibility_response = seal_pump_compatibility_gateway.list_seal_pump_compatibilities()
    compatible_seal_codes = [
        record.get("seal_code")
        for record in (compatibility_response.get("data") or [])
        if record.get("pump_tag_number") == tag_number
    ]

    seal_stock_gateway = seal_stock_gateway or SealStockGateway()
    stock_response = seal_stock_gateway.list_seal_stocks()
    stock_by_seal_code = {
        record.get("seal_code"): record for record in (stock_response.get("data") or [])
    }

    seal_gateway = seal_gateway or SealGateway()
    seal_response = seal_gateway.list_seals()
    seal_by_code = {record.get("seal_code"): record for record in (seal_response.get("data") or [])}

    spare_parts = []
    for seal_code in compatible_seal_codes:
        seal = seal_by_code.get(seal_code) or {}
        stock = stock_by_seal_code.get(seal_code) or {}
        spare_parts.append(
            {
                "seal_code": seal_code,
                "part_name": seal.get("seal_name"),
                "quantity_on_hand": stock.get("quantity_on_hand"),
                "reorder_point": stock.get("reorder_point"),
                "location": stock.get("location"),
            }
        )

    return {
        "success": compatibility_response.get("success", False),
        "tag_number": tag_number,
        "spare_parts": spare_parts,
    }


def get_active_work_orders(
    tag_number: str | None = None,
    work_order_gateway: WorkOrderGateway | None = None,
) -> dict[str, Any]:
    """Show Active Work Orders: open work orders from Work Order Gateway's
    existing list, optionally narrowed to one pump."""

    work_order_gateway = work_order_gateway or WorkOrderGateway()
    response = work_order_gateway.list_work_orders()
    work_orders = [wo for wo in (response.get("data") or []) if not wo.get("closed_at")]

    if tag_number:
        work_orders = [wo for wo in work_orders if wo.get("asset_code") == tag_number]

    return {
        "success": response.get("success", False),
        "work_orders": work_orders,
    }


def get_assigned_role(
    product_name: str,
    work_order_code: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
    work_order_gateway: WorkOrderGateway | None = None,
) -> dict[str, Any] | None:
    """Show Assigned Role: the Role artifact assigned to a work order, via
    Work Order Gateway's detail and Organization Registry."""

    work_order_gateway = work_order_gateway or WorkOrderGateway()
    response = work_order_gateway.get_work_order(work_order_code)

    if not response.get("success"):
        return None

    role_name = (response.get("data") or {}).get("assigned_to")

    if not role_name:
        return None

    return retrieve_role_artifact(product_name, role_name, root_path)


def get_recent_maintenance(
    product_name: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
    today: date | None = None,
    pump_gateway: PumpGateway | None = None,
    work_order_gateway: WorkOrderGateway | None = None,
    maintenance_history_gateway: MaintenanceHistoryGateway | None = None,
) -> list[dict[str, Any]]:
    """Show Recent Maintenance: reused unchanged from the Maintenance
    Command Center's already-computed recent maintenance list."""

    command_center = get_maintenance_command_center(
        product_name,
        root_path=root_path,
        today=today,
        pump_gateway=pump_gateway,
        work_order_gateway=work_order_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
    )

    return command_center["recent_maintenance"]


def summarize_situation(
    product_name: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
    today: date | None = None,
    pump_gateway: PumpGateway | None = None,
    work_order_gateway: WorkOrderGateway | None = None,
    maintenance_history_gateway: MaintenanceHistoryGateway | None = None,
    scope: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Summarize Current Situation: reused unchanged from the Maintenance
    Command Center."""

    return get_maintenance_command_center(
        product_name,
        root_path=root_path,
        today=today,
        pump_gateway=pump_gateway,
        work_order_gateway=work_order_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
        scope=scope,
    )


# MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017 -- three pure selection
# functions (list-of-records in, one selected record/aggregate out; no
# gateway call, no I/O of their own) backing the new fleet-wide Copilot
# intents (installation-history/latest, condition-monitoring/leak
# frequency, seal-code stock lookup). Kept pure and gateway-free, unlike
# this file's other functions, specifically so the caller
# (copilot_ask_service.py) can fetch once and apply its own Area/MA scope
# filter (pump_area_scope.filter_records_by_asset_scope, reused unmodified)
# to the raw records BEFORE selection -- filtering after selecting the
# "latest"/"most frequent" would risk silently discarding the correct
# in-scope answer in favor of an out-of-scope one nobody should see.


def select_latest_installation(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Given already-fetched (and, if applicable, already scope-filtered)
    installation_report records, returns the one with the most recent
    PARSEABLE report_date, or None if no record has one. Never guesses an
    order among undated records -- an undated record is simply excluded
    from "latest" consideration, not assumed oldest or newest."""

    def _parse_date(record: dict[str, Any]) -> date | None:
        raw = record.get("report_date")
        if not raw:
            return None
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            return None

    dated = [(record, parsed) for record in records if (parsed := _parse_date(record)) is not None]
    if not dated:
        return None
    dated.sort(key=lambda item: item[1], reverse=True)
    return dated[0][0]


def select_most_frequent_leak_pump(readings: list[dict[str, Any]]) -> tuple[str, int] | None:
    """Given already-fetched (and, if applicable, already scope-filtered)
    condition_monitoring_reading records, returns (asset_code, leak_count)
    for the pump with the most mechanical-seal-leak-flagged readings (DE or
    NDE side, the same flags get_pump_condition_monitoring_flag already
    reads), or None if none are flagged anywhere. Ties keep the
    first-encountered pump -- a real, disclosed, deterministic
    tie-break, never an arbitrary one."""
    counts: dict[str, int] = {}
    order: list[str] = []
    for reading in readings:
        if reading.get("mechanical_seal_leak_de") is not True and reading.get("mechanical_seal_leak_nde") is not True:
            continue
        asset_code = reading.get("asset_code")
        if not asset_code:
            continue
        if asset_code not in counts:
            counts[asset_code] = 0
            order.append(asset_code)
        counts[asset_code] += 1

    if not counts:
        return None
    top_asset_code = max(order, key=lambda asset_code: counts[asset_code])
    return top_asset_code, counts[top_asset_code]


# MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017A -- select_seal_stock
# (legacy seal_stock-table lookup) removed, not left dead: "legacy
# seal_stock MUST NOT contribute quantity" is enforced structurally by
# deleting the one function that read it for Copilot, not merely by no
# longer calling it. select_stock_v1_pools_by_seal_code below is its
# Stock V1 replacement.


def select_stock_v1_pools_by_seal_code(
    pools: list[dict[str, Any]], seal_code: str
) -> tuple[dict[str, Any], ...]:
    """Given already-fetched mechanical_seal_stock_pool records (Stock V1,
    MechanicalSealStockRepository.list_pools()'s own "items"/"data" list,
    reused unmodified -- no new SQL), returns every pool matching seal_code,
    in the order given.

    Matches against `seal_type`, not `seal_code` (disclosed, verified
    against real production data before writing this function):
    mechanical_seal_stock_pool.seal_code is NULL on every real production
    row (44/44) -- what users mean by "seal code" in a question like
    "stock seal T48MP" (T48MP, T6014DP, etc.) is this table's own
    `seal_type` value, confirmed by inspecting real rows (three separate
    pools genuinely carry seal_type='T48MP', each a different
    nominal_size). Case-insensitive exact match (never substring/ILIKE) so
    "t48mp" matches "T48MP" but "T48MP" never wrongly matches "T48LP".

    Deliberately returns ALL matches rather than picking one or summing
    them: no existing Stock V1 contract declares multiple pools for one
    seal_type as additive (the three real T48MP pools above are physically
    distinct stock, different sizes) -- the caller reports each pool
    separately when there is more than one."""
    target = seal_code.strip().upper()
    return tuple(pool for pool in pools if str(pool.get("seal_type") or "").strip().upper() == target)
