"""
MWO-LTSA-DASHBOARD-RECOVERY-001 -- BasicFleetOverviewService: bounded
fleet summary for the Executive Dashboard's core Fleet Overview, built
entirely from existing canonical bulk-list gateways -- exactly one call
per domain (list_pumps, list_work_orders, list_pm_schedules,
list_cm_reports, list_seal_stocks), never a per-pump loop.

This is deliberately separate from FleetReliabilityService/
FleetExecutiveSummaryService (both unchanged, untouched): those compute
MTBF/MTTR/health-score/critical-asset/top-risk metrics, which require
LTSAKnowledgeService.build(tag) once per pump (PM+CM+work-order+seal
history aggregation, itself n8n-backed) -- exactly the per-pump fan-out
that times out against a real fleet and exactly what this "basic"
overview must not require. Reliability/health-score metrics are
intentionally NOT reproduced here; the Executive Dashboard's Fleet
Overview shows only what this bounded read supports.

Scope enforcement: pumps are filtered by area at discovery, the same
choke point FleetReliabilityService already uses (is_area_in_scope,
applied before any count is taken). Work orders/PM schedules/CM reports
carry no area field of their own -- each is attributed to a pump via its
own asset_code (confirmed field name: workOrderMapping.js/pmMapping.js/
cmMapping.js all map record.asset_code), so they are scoped by
membership in the already-scoped pump tag set, never by a second scope
lookup or an unscoped read followed by discarding results.

Every field with no supporting data is empty/None, never fabricated.
Each gateway call degrades independently to empty on failure (OSError,
mirroring FleetReliabilityService._list_pump_tags's own precedent) --
one gateway being unreachable must never take down the whole overview.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable

from .cm_report_gateway import CMReportGateway
from .pm_schedule_gateway import PMScheduleGateway
from .pump_area_scope import is_area_in_scope
from .pump_gateway import PumpGateway
from .seal_stock_gateway import SealStockGateway
from .work_order_gateway import WorkOrderGateway


@dataclass(frozen=True, slots=True)
class BasicFleetOverview:
    """Immutable: one bounded fleet snapshot from canonical bulk-list
    gateways only. Fields with no supporting data are empty/None, never
    fabricated."""

    pump_count: int
    area_distribution: dict[str, int]
    status_distribution: dict[str, int]
    work_order_count: int
    work_order_status_distribution: dict[str, int]
    pm_schedule_count: int
    cm_report_count: int
    seal_stock_count: int
    low_stock_seal_count: int | None


class BasicFleetOverviewService:
    """One bounded call per domain gateway, aggregated in-process. No
    per-pump knowledge build, no n8n fan-out."""

    def __init__(
        self,
        pump_gateway: PumpGateway | None = None,
        work_order_gateway: WorkOrderGateway | None = None,
        pm_schedule_gateway: PMScheduleGateway | None = None,
        cm_report_gateway: CMReportGateway | None = None,
        seal_stock_gateway: SealStockGateway | None = None,
    ) -> None:
        self.pump_gateway = pump_gateway or PumpGateway()
        self.work_order_gateway = work_order_gateway or WorkOrderGateway()
        self.pm_schedule_gateway = pm_schedule_gateway or PMScheduleGateway()
        self.cm_report_gateway = cm_report_gateway or CMReportGateway()
        self.seal_stock_gateway = seal_stock_gateway or SealStockGateway()

    def build(self, *, scope: frozenset[str] | None = None) -> BasicFleetOverview:
        pumps = self._list_scoped_pumps(scope)
        scoped_tags = {p.get("tag_number") for p in pumps if p.get("tag_number")}

        work_orders = self._scoped_by_asset_code(
            _safe_list(self.work_order_gateway.list_work_orders), scoped_tags
        )
        pm_schedules = self._scoped_by_asset_code(
            _safe_list(self.pm_schedule_gateway.list_pm_schedules), scoped_tags
        )
        cm_reports = self._scoped_by_asset_code(
            _safe_list(self.cm_report_gateway.list_cm_reports), scoped_tags
        )
        # Seal stock is not pump-attributed (spare-part inventory, not a
        # per-asset record) -- reported fleet-wide, unscoped, matching
        # SealStockGateway's own "location"-only granularity.
        seal_stocks = _safe_list(self.seal_stock_gateway.list_seal_stocks)

        return BasicFleetOverview(
            pump_count=len(pumps),
            area_distribution=_distribution(pumps, "area"),
            status_distribution=_distribution(pumps, "status"),
            work_order_count=len(work_orders),
            work_order_status_distribution=_distribution(work_orders, "status"),
            pm_schedule_count=len(pm_schedules),
            cm_report_count=len(cm_reports),
            seal_stock_count=len(seal_stocks),
            low_stock_seal_count=_count_low_stock(seal_stocks),
        )

    def _list_scoped_pumps(self, scope: frozenset[str] | None) -> list[dict[str, Any]]:
        # Tagless records are skipped -- the same precedent
        # FleetReliabilityService._list_pump_tags already establishes;
        # without a tag_number a record cannot be attributed to any
        # work order/PM schedule/CM report via asset_code either.
        records = [r for r in _safe_list(self.pump_gateway.list_pumps) if r.get("tag_number")]
        if scope is not None:
            records = [r for r in records if is_area_in_scope(r.get("area"), scope)]
        return records

    @staticmethod
    def _scoped_by_asset_code(
        records: list[dict[str, Any]], scoped_tags: set[str]
    ) -> list[dict[str, Any]]:
        return [r for r in records if r.get("asset_code") in scoped_tags]


def _safe_list(list_fn: Callable[[], dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        response = list_fn()
    except OSError:
        return []
    return response.get("data") or []


def _distribution(records: list[dict[str, Any]], field_name: str) -> dict[str, int]:
    counts = Counter(r.get(field_name) for r in records if r.get(field_name))
    return dict(counts)


def _count_low_stock(seal_stocks: list[dict[str, Any]]) -> int | None:
    known = [
        r
        for r in seal_stocks
        if r.get("quantity_on_hand") is not None and r.get("reorder_point") is not None
    ]
    if not known:
        return None
    return sum(1 for r in known if r["quantity_on_hand"] <= r["reorder_point"])


__all__ = ["BasicFleetOverview", "BasicFleetOverviewService"]
