"""
MWO-LTSA-031A -- LTSAKnowledgeService: aggregates existing LTSA domain
gateways/services into one LTSAKnowledge object per pump. No SQL, no
repository layer, no duplicated business logic -- pump, seal, inventory,
and cm_history's "latest" cousins are all obtained from
maintenance_intelligence_service's existing wrappers unchanged.

pm_history, cm_history, and breakdown_history have no existing MIS
wrapper returning a full list (only get_pump_last_pm/get_pump_last_cm's
single latest record, confirmed by repository archaeology) -- each is
gathered directly from its Gateway, filtered by asset_code, the same
"filter first" technique EngineeringContextEngine already uses for
pm_schedule and cm_report's open-status scan. breakdown_history reuses
EngineeringContextEngine._build_maintenance_summary's own established
definition of "breakdown" (a maintenance_history record whose linked
work order has work_type == 'CM'), generalized from "latest" to the
full list -- not a new business rule.

drawings and recommendation have no backend service to aggregate today:
Drawing exists only as frontend mock data (RC-003A-C); recommendation
exists only via the AI copilot's non-deterministic LLM pipeline, out of
scope for a pure aggregation service. Both are disclosed as None rather
than fabricated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import maintenance_intelligence_service as mis
from .cm_report_gateway import CMReportGateway
from .maintenance_history_gateway import MaintenanceHistoryGateway
from .pm_occurrence_gateway import PMOccurrenceGateway
from .pump_gateway import PumpGateway
from .seal_gateway import SealGateway
from .seal_pump_compatibility_gateway import SealPumpCompatibilityGateway
from .seal_stock_gateway import SealStockGateway
from .work_order_gateway import WorkOrderGateway


@dataclass(frozen=True, slots=True)
class LTSAKnowledge:
    """Immutable aggregate: one pump's knowledge across every existing
    LTSA domain service."""

    tag_number: str
    pump: dict[str, Any] | None
    seal: list[dict[str, Any]]
    inventory: list[dict[str, Any]]
    pm_history: list[dict[str, Any]]
    cm_history: list[dict[str, Any]]
    breakdown_history: list[dict[str, Any]]
    drawings: Any
    recommendation: Any


class LTSAKnowledgeService:
    """Aggregates existing LTSA services/gateways into LTSAKnowledge. No
    SQL, no repository layer, no duplicated business logic -- every
    dependency is injected, defaulting to its real implementation."""

    def __init__(
        self,
        pump_gateway: PumpGateway | None = None,
        maintenance_history_gateway: MaintenanceHistoryGateway | None = None,
        pm_occurrence_gateway: PMOccurrenceGateway | None = None,
        cm_report_gateway: CMReportGateway | None = None,
        seal_gateway: SealGateway | None = None,
        seal_stock_gateway: SealStockGateway | None = None,
        seal_pump_compatibility_gateway: SealPumpCompatibilityGateway | None = None,
        work_order_gateway: WorkOrderGateway | None = None,
    ) -> None:
        self.pump_gateway = pump_gateway or PumpGateway()
        self.maintenance_history_gateway = maintenance_history_gateway or MaintenanceHistoryGateway()
        self.pm_occurrence_gateway = pm_occurrence_gateway or PMOccurrenceGateway()
        self.cm_report_gateway = cm_report_gateway or CMReportGateway()
        self.seal_gateway = seal_gateway or SealGateway()
        self.seal_stock_gateway = seal_stock_gateway or SealStockGateway()
        self.seal_pump_compatibility_gateway = (
            seal_pump_compatibility_gateway or SealPumpCompatibilityGateway()
        )
        self.work_order_gateway = work_order_gateway or WorkOrderGateway()

    def build(self, tag_number: str) -> LTSAKnowledge:
        spare_parts = self._build_spare_parts(tag_number)

        return LTSAKnowledge(
            tag_number=tag_number,
            pump=self._build_pump(tag_number),
            seal=[
                {"seal_code": part["seal_code"], "part_name": part["part_name"]}
                for part in spare_parts
            ],
            inventory=[
                {
                    "seal_code": part["seal_code"],
                    "quantity_on_hand": part["quantity_on_hand"],
                    "reorder_point": part["reorder_point"],
                    "location": part["location"],
                }
                for part in spare_parts
            ],
            pm_history=self._build_pm_history(tag_number),
            cm_history=self._build_cm_history(tag_number),
            breakdown_history=self._build_breakdown_history(tag_number),
            drawings=None,
            recommendation=None,
        )

    def _build_pump(self, tag_number: str) -> dict[str, Any] | None:
        response = mis.get_pump_status(tag_number, pump_gateway=self.pump_gateway)
        return response.get("data") if response.get("success") else None

    def _build_spare_parts(self, tag_number: str) -> list[dict[str, Any]]:
        result = mis.get_pump_spare_parts(
            tag_number,
            seal_pump_compatibility_gateway=self.seal_pump_compatibility_gateway,
            seal_stock_gateway=self.seal_stock_gateway,
            seal_gateway=self.seal_gateway,
        )
        return result.get("spare_parts") or []

    def _build_pm_history(self, tag_number: str) -> list[dict[str, Any]]:
        response = self.pm_occurrence_gateway.list_pm_occurrences()
        return [
            record
            for record in (response.get("data") or [])
            if record.get("asset_code") == tag_number
        ]

    def _build_cm_history(self, tag_number: str) -> list[dict[str, Any]]:
        response = self.cm_report_gateway.list_cm_reports()
        return [
            record
            for record in (response.get("data") or [])
            if record.get("asset_code") == tag_number
        ]

    def _build_breakdown_history(self, tag_number: str) -> list[dict[str, Any]]:
        history = mis.get_pump_history(
            tag_number, maintenance_history_gateway=self.maintenance_history_gateway
        )
        records = history.get("records") or []

        work_orders_response = self.work_order_gateway.list_work_orders()
        work_order_types = {
            wo.get("work_order_code"): wo.get("work_type")
            for wo in (work_orders_response.get("data") or [])
        }

        return [
            record for record in records if work_order_types.get(record.get("work_order_code")) == "CM"
        ]


__all__ = ["LTSAKnowledge", "LTSAKnowledgeService"]
