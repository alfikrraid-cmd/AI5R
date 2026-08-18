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

drawings (MWO-LTSA-033): populated from seal_engineering_document
(BP-SEAL-ENGINEERING-DOCUMENT, MWO-LTSA-030/040B), filtered to
document_type == 'DRAWING' and to the seal_codes already found compatible
with this pump by _build_spare_parts -- no second compatibility-gateway
call. Repository archaeology considered two other candidate sources and
rejected both: pdf_document (MWO-040D, document_type has a
'JOHN_CRANE_DRAWING' value) carries no seal_code/pump_tag_number FK at
all, and document_field_extraction (Document Upload MVP, has a direct
pump_tag_number FK and a 'PUMP_DRAWING'/'MECHANICAL_SEAL_DRAWING'
detected_document_type) has no document_number/revision columns -- both
of this MWO's required fields would have to be guessed out of a JSONB
blob rather than read from a real column. seal_engineering_document is
the only source with all seven required fields (drawing_id, title,
document_number, revision, status, file_name, uploaded_at) as real
columns. uploaded_at maps from created_at (when the row was acquired
into this system), not issue_date (the drawing's own issuance date) --
a disclosed judgment call, not a fabricated fact. Metadata only, per this
MWO's explicit scope -- file_reference (the pointer to the binary) is
never included in the mapped shape.

recommendation (MWO-LTSA-032C): now populated by the existing, unmodified
RecommendationEngine (MWO-LTSA-031F/R1), constructor-injected the same
way every gateway here already is. RecommendationEngine.recommend() is a
pure function of an already-built LTSAKnowledge -- build() therefore
constructs the aggregate once with recommendation left at its empty-tuple
placeholder, then returns a single dataclasses.replace() with the real
result, rather than duplicating the constructor call or mutating a frozen
instance.

pm_schedules / condition_monitoring_schedules (MWO-LTSA-036E, Asset360
Migration Roadmap Phase 2): same "filter by asset_code" technique already
used for pm_history/cm_history -- no new business rule. PMScheduleGateway
is reused unmodified (already consumed the same way by
EngineeringContextEngine); ConditionMonitoringScheduleGateway is reused
unmodified (already constructor-wired in dependencies.py, previously
unused by any service). No new gateway, no new endpoint -- both fields
are additive keys on the same LTSAKnowledge aggregate and the same
GET /api/ltsa/pumps/{tag}/knowledge response, per the Chief Architect's
explicit "One Aggregate -> One API -> One Fetch" directive.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from . import maintenance_intelligence_service as mis
from .cm_report_gateway import CMReportGateway
from .condition_monitoring_reading_gateway import ConditionMonitoringReadingGateway
from .condition_monitoring_schedule_gateway import ConditionMonitoringScheduleGateway
from .maintenance_history_gateway import MaintenanceHistoryGateway
from .pm_occurrence_gateway import PMOccurrenceGateway
from .pm_schedule_gateway import PMScheduleGateway
from .pump_gateway import PumpGateway
from .recommendation_engine import RecommendationEngine
from .seal_engineering_document_gateway import SealEngineeringDocumentGateway
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
    pm_schedules: list[dict[str, Any]]
    condition_monitoring_schedules: list[dict[str, Any]]
    condition_monitoring_readings: list[dict[str, Any]]


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
        recommendation_engine: RecommendationEngine | None = None,
        seal_engineering_document_gateway: SealEngineeringDocumentGateway | None = None,
        pm_schedule_gateway: PMScheduleGateway | None = None,
        condition_monitoring_schedule_gateway: ConditionMonitoringScheduleGateway | None = None,
        condition_monitoring_reading_gateway: ConditionMonitoringReadingGateway | None = None,
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
        self.recommendation_engine = recommendation_engine or RecommendationEngine()
        self.seal_engineering_document_gateway = (
            seal_engineering_document_gateway or SealEngineeringDocumentGateway()
        )
        self.pm_schedule_gateway = pm_schedule_gateway or PMScheduleGateway()
        self.condition_monitoring_schedule_gateway = (
            condition_monitoring_schedule_gateway or ConditionMonitoringScheduleGateway()
        )
        self.condition_monitoring_reading_gateway = (
            condition_monitoring_reading_gateway or ConditionMonitoringReadingGateway()
        )

    def build(self, tag_number: str) -> LTSAKnowledge:
        spare_parts = self._build_spare_parts(tag_number)

        knowledge = LTSAKnowledge(
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
            drawings=self._build_drawings(spare_parts),
            recommendation=(),
            pm_schedules=self._build_pm_schedules(tag_number),
            condition_monitoring_schedules=self._build_condition_monitoring_schedules(tag_number),
            condition_monitoring_readings=self._build_condition_monitoring_readings(tag_number),
        )

        return replace(knowledge, recommendation=self.recommendation_engine.recommend(knowledge))

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

    def _build_drawings(self, spare_parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compatible_seal_codes = {part["seal_code"] for part in spare_parts}
        response = self.seal_engineering_document_gateway.list_seal_engineering_documents()

        return [
            {
                "drawing_id": record.get("document_code"),
                "title": record.get("title"),
                "document_number": record.get("document_number"),
                "revision": record.get("revision"),
                "status": record.get("status"),
                "file_name": record.get("file_name"),
                "uploaded_at": record.get("created_at"),
            }
            for record in (response.get("data") or [])
            if record.get("document_type") == "DRAWING"
            and record.get("seal_code") in compatible_seal_codes
        ]

    def _build_pm_schedules(self, tag_number: str) -> list[dict[str, Any]]:
        response = self.pm_schedule_gateway.list_pm_schedules()
        return [
            record
            for record in (response.get("data") or [])
            if record.get("asset_code") == tag_number
        ]

    def _build_condition_monitoring_schedules(self, tag_number: str) -> list[dict[str, Any]]:
        response = self.condition_monitoring_schedule_gateway.list_condition_monitoring_schedules()
        return [
            record
            for record in (response.get("data") or [])
            if record.get("asset_code") == tag_number
        ]

    def _build_condition_monitoring_readings(self, tag_number: str) -> list[dict[str, Any]]:
        response = self.condition_monitoring_reading_gateway.list_condition_monitoring_readings()
        return [
            record
            for record in (response.get("data") or [])
            if record.get("asset_code") == tag_number
        ]

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
