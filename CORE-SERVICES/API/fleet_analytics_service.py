"""MWO-LTSA-FLEET-ANALYTICS-001 -- canonical fleet-wide analytical read
layer, built directly on top of Canonical Equipment 360's own already-
established data sources (never a second/divergent source).

ROOT CAUSE this module exists to fix: every prior fleet-wide query
(FleetReliabilityService.list_pump_knowledge(), and this module's own new
queries) needed several per-pump facts (condition_monitoring_readings,
cm_history, pm_history, compatible seals, breakdown history) that were
previously fetched via LTSAKnowledgeService.build(tag) called ONCE PER
PUMP -- and several of THOSE per-pump calls (seal_pump_compatibility_
gateway.list_seal_pump_compatibilities(), seal_gateway.list_seals(),
work_order_gateway.list_work_orders(), maintenance_history_gateway.
list_maintenance_history()) were themselves already unfiltered "list
every row in the table" calls, redundantly refetching the IDENTICAL
fleet-wide dataset for every single pump. For an N-pump fleet this is
O(N) redundant network round-trips to n8n for data that could have been
fetched exactly once.

build_fleet_data_batch() fetches every canonical source EXACTLY ONCE
(condition_monitoring_reading_repository.list_all(), cm_report_
repository.list_cm_reports(), the new pm_occurrence_repository.list_all(),
pm_schedule_repository.list_pm_schedules(), seal_pump_compatibility_
gateway.list_seal_pump_compatibilities(), seal_gateway.list_seals(),
mechanical_seal_stock_repository.list_pools(), work_order_gateway.
list_work_orders(), maintenance_history_gateway.list_maintenance_
history()) and groups each result by asset_code/equipment_tag in memory
-- O(1) total calls regardless of fleet size, never a data-fetch-time
filter that could hide records, only a rendering/grouping convenience.

Every query function below reads ONLY from this pre-fetched batch --
none makes its own gateway/repository call.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from . import maintenance_intelligence_service as mis
from .condition_monitoring_measurement_fields import fields_matching_search_term, parameter_values
from .pump_area_scope import is_area_in_scope

STOCK_AVAILABLE = "AVAILABLE"
STOCK_ZERO = "ZERO_STOCK"
STOCK_NO_RECORD = "NO_STOCK_RECORD"
STOCK_NO_COMPATIBLE_SEAL = "NO_COMPATIBLE_SEAL"

DEFAULT_RANKING_LIMIT = 5


@dataclass(frozen=True, slots=True)
class FleetDataBatch:
    pumps: tuple[dict[str, Any], ...]
    cmon_by_tag: dict[str, tuple[dict[str, Any], ...]]
    cm_by_tag: dict[str, tuple[dict[str, Any], ...]]
    pm_by_tag: dict[str, tuple[dict[str, Any], ...]]
    pm_schedule_by_tag: dict[str, tuple[dict[str, Any], ...]]
    compatible_seals_by_tag: dict[str, tuple[dict[str, Any], ...]]
    stock_rows: tuple[dict[str, Any], ...]
    breakdown_by_tag: dict[str, tuple[dict[str, Any], ...]]
    data_gaps: tuple[str, ...]


def _group_by(rows: list[dict[str, Any]], key_field: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = row.get(key_field)
        if key:
            grouped.setdefault(key, []).append(row)
    return grouped


def build_fleet_data_batch(
    *,
    pump_gateway,
    condition_monitoring_reading_repository,
    cm_report_repository,
    pm_occurrence_repository,
    pm_schedule_repository,
    seal_pump_compatibility_gateway,
    seal_gateway,
    mechanical_seal_stock_repository,
    work_order_gateway=None,
    maintenance_history_gateway=None,
    scope: frozenset[str] | None = None,
) -> FleetDataBatch:
    gaps: list[str] = []

    pumps: tuple[dict[str, Any], ...] = ()
    try:
        response = pump_gateway.list_pumps()
        pumps_all = response.get("data") or [] if response.get("success") else []
        pumps = tuple(
            p for p in pumps_all if scope is None or is_area_in_scope(p.get("area"), scope)
        )
    except Exception:
        gaps.append("pumps")

    cmon_by_tag: dict[str, tuple[dict[str, Any], ...]] = {}
    try:
        # condition_monitoring_reading_repository.list_all() returns a
        # dict ({"success", "data", "count", "total", ...} -- the same
        # shape its own list_by_asset()-sibling "list ALL" methods use
        # elsewhere in this codebase, e.g. cm_report_repository.
        # list_cm_reports()), NOT a bare list -- unwrap it the same way
        # every other dict-shaped "list ALL" call in this function
        # already does. (Caught in production: an earlier version of
        # this function treated the return value as a bare list, which
        # silently produced an EMPTY cmon_by_tag on every real call --
        # never a crash, since the dict itself is truthy/iterable-as-keys,
        # just a wrong-shape produces zero rows.)
        response = condition_monitoring_reading_repository.list_all(scope=scope, limit=20000)
        rows = (response.get("data") or []) if response.get("success") else []
        cmon_by_tag = {k: tuple(v) for k, v in _group_by(list(rows), "asset_code").items()}
    except Exception:
        gaps.append("cmon")

    cm_by_tag: dict[str, tuple[dict[str, Any], ...]] = {}
    try:
        response = cm_report_repository.list_cm_reports(scope=scope)
        if response.get("success"):
            cm_by_tag = {k: tuple(v) for k, v in _group_by(response.get("data") or [], "asset_code").items()}
        else:
            gaps.append("cm")
    except Exception:
        gaps.append("cm")

    pm_by_tag: dict[str, tuple[dict[str, Any], ...]] = {}
    try:
        rows = pm_occurrence_repository.list_all(scope=scope, limit=20000)
        pm_by_tag = {k: tuple(v) for k, v in _group_by(list(rows or []), "asset_code").items()}
    except Exception:
        gaps.append("pm")

    pm_schedule_by_tag: dict[str, tuple[dict[str, Any], ...]] = {}
    try:
        response = pm_schedule_repository.list_pm_schedules(scope=scope)
        if response.get("success"):
            pm_schedule_by_tag = {k: tuple(v) for k, v in _group_by(response.get("data") or [], "asset_code").items()}
        else:
            gaps.append("pm_schedule")
    except Exception:
        gaps.append("pm_schedule")

    # Compatible seals: TWO calls total, not per pump -- pump_tag_number ->
    # [{"seal_code":..., "part_name":...}], the same shape LTSAKnowledge
    # Service._build_compatible_seals already produces per pump.
    compatible_seals_by_tag: dict[str, tuple[dict[str, Any], ...]] = {}
    try:
        compat_response = seal_pump_compatibility_gateway.list_seal_pump_compatibilities()
        seals_response = seal_gateway.list_seals()
        seal_by_code = {s.get("seal_code"): s for s in (seals_response.get("data") or [])}
        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in (compat_response.get("data") or []):
            tag = record.get("pump_tag_number")
            code = record.get("seal_code")
            if not tag or not code:
                continue
            seal = seal_by_code.get(code) or {}
            grouped.setdefault(tag, []).append({"seal_code": code, "part_name": seal.get("seal_name")})
        compatible_seals_by_tag = {k: tuple(v) for k, v in grouped.items()}
    except Exception:
        gaps.append("compatible_seals")

    stock_rows: tuple[dict[str, Any], ...] = ()
    try:
        response = mechanical_seal_stock_repository.list_pools(limit=200)
        if response.get("success"):
            stock_rows = mis.flatten_stock_v1_fleet_rows(response.get("data") or [])
        else:
            gaps.append("stock")
    except Exception:
        gaps.append("stock")

    # Breakdown history (CM-type maintenance_history records) -- same
    # derivation LTSAKnowledgeService._build_breakdown_history already
    # uses, applied to batch-fetched (not per-pump) work_orders/
    # maintenance_history. Optional: a caller not supplying these two
    # gateways simply gets breakdown_by_tag={} (REC_REPEATED_BREAKDOWN
    # never fires, disclosed limitation -- every other recommendation
    # rule this module supports is unaffected).
    breakdown_by_tag: dict[str, tuple[dict[str, Any], ...]] = {}
    if work_order_gateway is not None and maintenance_history_gateway is not None:
        try:
            wo_response = work_order_gateway.list_work_orders()
            work_order_types = {
                wo.get("work_order_code"): wo.get("work_type") for wo in (wo_response.get("data") or [])
            }
            history_response = maintenance_history_gateway.list_maintenance_history()
            grouped_bd: dict[str, list[dict[str, Any]]] = {}
            for record in (history_response.get("data") or []):
                if work_order_types.get(record.get("work_order_code")) != "CM":
                    continue
                tag = record.get("asset_code")
                if tag:
                    grouped_bd.setdefault(tag, []).append(record)
            breakdown_by_tag = {k: tuple(v) for k, v in grouped_bd.items()}
        except Exception:
            gaps.append("breakdown_history")

    return FleetDataBatch(
        pumps=pumps,
        cmon_by_tag=cmon_by_tag,
        cm_by_tag=cm_by_tag,
        pm_by_tag=pm_by_tag,
        pm_schedule_by_tag=pm_schedule_by_tag,
        compatible_seals_by_tag=compatible_seals_by_tag,
        stock_rows=stock_rows,
        breakdown_by_tag=breakdown_by_tag,
        data_gaps=tuple(gaps),
    )


# -- Generic parameter ranking (Phase 4/6) ------------------------------------


@dataclass(frozen=True, slots=True)
class ParameterRankingRow:
    equipment_tag: str
    label: str
    value: float
    unit: str
    reading_date: Any


def rank_by_parameter(
    batch: FleetDataBatch, search_term: str, *, limit: int = DEFAULT_RANKING_LIMIT
) -> tuple[tuple[ParameterRankingRow, ...], int, int]:
    """Ranks pumps by their OWN latest CMON event's highest value among
    fields matching `search_term` -- "latest comparable measurement", not
    an all-time maximum (Phase 4's own explicit aggregation rule). A pump
    with no CMON reading, or whose latest reading has no value for this
    parameter, is excluded from the ranking (never treated as zero) but
    counted in the returned population totals. Returns (ranked_rows,
    evaluated_population, population_with_data)."""
    fields = fields_matching_search_term(search_term)
    rows: list[ParameterRankingRow] = []
    evaluated = 0
    with_data = 0
    for pump in batch.pumps:
        tag = pump.get("tag_number")
        if not tag:
            continue
        evaluated += 1
        readings = batch.cmon_by_tag.get(tag, ())
        if not readings:
            continue
        latest = readings[0]  # cmon_by_tag preserves list_all()'s own ORDER BY reading_date DESC
        values = parameter_values(latest, fields)
        if not values:
            continue
        with_data += 1
        name, value, unit = max(values, key=lambda item: item[1])
        rows.append(ParameterRankingRow(tag, name, value, unit, latest.get("reading_date")))
    ranked = tuple(sorted(rows, key=lambda r: r.value, reverse=True))
    return ranked[:limit], evaluated, with_data


# -- Current / active leak (Phase 7) ------------------------------------------


@dataclass(frozen=True, slots=True)
class CurrentLeakRow:
    equipment_tag: str
    reading_date: Any
    finding: str | None
    workflow_status: str | None


def current_leak_pumps(batch: FleetDataBatch, *, today: date | None = None) -> tuple[CurrentLeakRow, ...]:
    """Reuses maintenance_intelligence_service.leak_flag_from_readings --
    the SAME canonical 30-day active-monitoring window RecommendationEngine's
    own REC_ACTIVE_LEAK rule and copilot_ask_service's fleet-priority path
    already use. Never a second, conflicting definition of "current"."""
    rows: list[CurrentLeakRow] = []
    for pump in batch.pumps:
        tag = pump.get("tag_number")
        if not tag:
            continue
        readings = batch.cmon_by_tag.get(tag, ())
        flag = mis.leak_flag_from_readings(list(readings), today=today)
        if flag["flagged"] and flag["latest_flagged_reading"]:
            record = flag["latest_flagged_reading"]
            rows.append(CurrentLeakRow(tag, record.get("reading_date"), record.get("finding"), record.get("workflow_status")))
    return tuple(rows)


# -- Historical leak frequency (Phase 8) --------------------------------------


@dataclass(frozen=True, slots=True)
class LeakFrequencyRow:
    equipment_tag: str
    count: int


def _parse_date(value: Any):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def historical_leak_frequency(
    batch: FleetDataBatch, period, *, limit: int = DEFAULT_RANKING_LIMIT
) -> tuple[tuple[LeakFrequencyRow, ...], int]:
    """Counts leak-flagged CMON events strictly inside [period.start,
    period.end] -- never an all-time count, never a substitute for the
    current-leak query above. Returns (ranked_rows, matching_pump_count)."""
    rows: list[LeakFrequencyRow] = []
    for pump in batch.pumps:
        tag = pump.get("tag_number")
        if not tag:
            continue
        count = 0
        for record in batch.cmon_by_tag.get(tag, ()):
            reading_date = _parse_date(record.get("reading_date"))
            if reading_date is None or not (period.start <= reading_date <= period.end):
                continue
            if record.get("mechanical_seal_leak_de") is True or record.get("mechanical_seal_leak_nde") is True:
                count += 1
        if count > 0:
            rows.append(LeakFrequencyRow(tag, count))
    ranked = tuple(sorted(rows, key=lambda r: r.count, reverse=True))
    return ranked[:limit], len(ranked)


# -- Stock semantics (Phase 9/10/11) ------------------------------------------


@dataclass(frozen=True, slots=True)
class StockStateRow:
    equipment_tag: str
    state: str
    seal_code: str | None
    quantity_available: int | None
    nominal_size: Any = None
    size_unit: Any = None
    stock_location: Any = None


def classify_fleet_stock(batch: FleetDataBatch) -> tuple[StockStateRow, ...]:
    """One row PER (equipment, compatible seal) pair -- a pump with
    multiple compatible seals in different states is never collapsed into
    one verdict (Phase 9's own explicit "never collapse these states").
    NO_COMPATIBLE_SEAL: no compatibility mapping exists at all.
    NO_STOCK_RECORD: a compatible seal exists but Stock V1 has no pool row
    for it. ZERO_STOCK: a real pool row exists with quantity_available==0.
    AVAILABLE: a real pool row exists with quantity_available > 0. An
    unknown (None) quantity_available on a real row is treated as
    NO_STOCK_RECORD-equivalent -- never coerced to 0 or to "available"."""
    stock_index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in batch.stock_rows:
        key = (row["equipment_tag"], (row.get("seal_type") or "").upper())
        stock_index[key] = row

    results: list[StockStateRow] = []
    for pump in batch.pumps:
        tag = pump.get("tag_number")
        if not tag:
            continue
        compatible = batch.compatible_seals_by_tag.get(tag, ())
        if not compatible:
            results.append(StockStateRow(tag, STOCK_NO_COMPATIBLE_SEAL, None, None))
            continue
        for seal in compatible:
            code = seal.get("seal_code")
            stock_row = stock_index.get((tag, (code or "").upper()))
            if stock_row is None or stock_row.get("quantity_available") is None:
                results.append(StockStateRow(tag, STOCK_NO_RECORD, code, None))
            elif stock_row["quantity_available"] == 0:
                results.append(StockStateRow(
                    tag, STOCK_ZERO, code, 0,
                    stock_row.get("nominal_size"), stock_row.get("size_unit"), stock_row.get("stock_location"),
                ))
            else:
                results.append(StockStateRow(
                    tag, STOCK_AVAILABLE, code, stock_row["quantity_available"],
                    stock_row.get("nominal_size"), stock_row.get("size_unit"), stock_row.get("stock_location"),
                ))
    return tuple(results)


# -- PM overdue (Phase 12) -----------------------------------------------------


def overdue_pm_pumps(batch: FleetDataBatch, *, today: date | None = None) -> tuple[tuple[str, Any], ...]:
    """Overdue is classified ONLY from real pm_schedule.next_due evidence
    (the same EngineeringContextEngine._compute_pm_status logic PM-due
    recommendations already use) -- never inferred from PM occurrence age
    alone. A pump with no schedule row is UNSCHEDULED, never OVERDUE."""
    from .engineering_context_engine import EngineeringContextEngine

    today = today or date.today()
    results: list[tuple[str, Any]] = []
    for pump in batch.pumps:
        tag = pump.get("tag_number")
        if not tag:
            continue
        schedules = batch.pm_schedule_by_tag.get(tag, ())
        schedules_sorted = sorted(schedules, key=lambda record: record.get("next_due") or "")
        schedule = schedules_sorted[0] if schedules_sorted else None
        status = EngineeringContextEngine._compute_pm_status(schedule, today)
        if status == "OVERDUE":
            results.append((tag, schedule.get("next_due")))
    return tuple(results)


__all__ = [
    "FleetDataBatch",
    "build_fleet_data_batch",
    "ParameterRankingRow",
    "rank_by_parameter",
    "CurrentLeakRow",
    "current_leak_pumps",
    "LeakFrequencyRow",
    "historical_leak_frequency",
    "StockStateRow",
    "classify_fleet_stock",
    "overdue_pm_pumps",
    "STOCK_AVAILABLE",
    "STOCK_ZERO",
    "STOCK_NO_RECORD",
    "STOCK_NO_COMPATIBLE_SEAL",
    "DEFAULT_RANKING_LIMIT",
]
