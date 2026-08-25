"""
MWO-LTSA-031B / R1 -- EquipmentTimelineService: aggregates the 7
canonical Timeline categories (PM, CM, Breakdown, Seal Replacement,
Inspection, Inventory Event, Recommendation) into one chronological
(oldest-first) TimelineEvent sequence per pump. No SQL, no API, no
React, no Workflow, no Router, no Gateway changes.

Reuse before create: PM, CM, and Breakdown history are obtained entirely
from LTSAKnowledgeService (MWO-LTSA-031A), constructor-injected -- this
module performs zero gateway calls and zero asset_code filtering of its
own; it only reshapes and merges already-correct lists into canonical
TimelineEvent instances.

Per Chief Architect decision (MWO-LTSA-031B-R1): Seal Replacement,
Inspection, Inventory Event, and Recommendation are canonical Timeline
categories, not "blocked" ones -- they simply have no populated data
today. Each has its own builder method, always returning a tuple (never
None), so the category is self-documenting in code and is a ready,
isolated extension point:
  - Seal Replacement, Inspection, Inventory Event: no canonical domain
    owner exists yet. ADR-LTSA-EVENT-001 (status: PROPOSED, not
    approved) lists all three among its own unresolved Open Questions
    (Section 13, Q6) and its Non-Goals (Section 9) forbid that ADR from
    defining storage/fields/APIs for them. ADR-WO-002 (line 120)
    separately confirms "INSPECTION" is dashboard mock data only, with
    no backing table. SealStockGateway exposes only a current-snapshot
    list_seal_stocks() -- no movement/transaction history to aggregate.
  - Recommendation: only the AI copilot's non-deterministic LLM pipeline
    produces recommendations; no deterministic data source exists, and
    per this MWO's own Section 5 ("No Recommendation logic"), no LLM
    call is made here.

No heuristic classification is invented for any of the four. Filling
one in later will not require touching PM/CM/Breakdown or the merge/
sort logic.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .installation_gateway import InstallationGateway
from .ltsa_knowledge_service import LTSAKnowledgeService
from .maintenance_history_gateway import MaintenanceHistoryGateway
from .maintenance_intelligence_service import get_active_work_orders, get_pump_last_cm, get_pump_last_pm
from .pm_occurrence_gateway import PMOccurrenceGateway
from .pump_lifecycle_models import (
    PumpLifecycle,
    PumpLifecycleAnalytics,
    PumpLifecycleCurrentInstallation,
    PumpLifecycleCurrentSeal,
    PumpLifecycleCurrentState,
    PumpLifecycleRelatedEngineering,
)
from .seal_gateway import SealGateway
from .timeline_value_objects import (
    EquipmentTimeline,
    TimelineCategory,
    TimelineEvent,
    TimelineSeverity,
    TimelineSource,
)
from .work_order_gateway import WorkOrderGateway

# MWO-LTSA-SEAL-EQUIPMENT-HISTORY-INTEGRATION-001 -- optional, additive:
# every seal-domain repository is a constructor default of None so every
# existing caller/test that never passes one keeps building() exactly as
# before (Hard Rule: "Equipment History with existing PM/CMON but no
# seal data must continue working unchanged").
from .seal_equipment_history_service import build_seal_events_for_pump, linked_installation_codes_for_pump


class EquipmentTimelineService:
    """Aggregates existing LTSA history into one chronological timeline.
    No SQL, no repository layer, no duplicated business logic -- PM, CM,
    and Breakdown filtering is never re-derived here; it is obtained
    unchanged from LTSAKnowledgeService."""

    def __init__(
        self,
        knowledge_service: LTSAKnowledgeService | None = None,
        installation_gateway: InstallationGateway | None = None,
        work_order_gateway: WorkOrderGateway | None = None,
        maintenance_history_gateway: MaintenanceHistoryGateway | None = None,
        pm_occurrence_gateway: PMOccurrenceGateway | None = None,
        seal_gateway: SealGateway | None = None,
        seal_lifecycle_event_repository: Any | None = None,
        seal_inspection_repository: Any | None = None,
        seal_repair_repository: Any | None = None,
        seal_warranty_assessment_repository: Any | None = None,
        installation_report_fitment_repository: Any | None = None,
    ) -> None:
        self._knowledge_service = knowledge_service or LTSAKnowledgeService()
        self._installation_gateway = installation_gateway or InstallationGateway()
        self._work_order_gateway = work_order_gateway or WorkOrderGateway()
        self._maintenance_history_gateway = maintenance_history_gateway or MaintenanceHistoryGateway()
        self._pm_occurrence_gateway = pm_occurrence_gateway or PMOccurrenceGateway()
        self._seal_gateway = seal_gateway or SealGateway()
        self._seal_lifecycle_event_repository = seal_lifecycle_event_repository
        self._seal_inspection_repository = seal_inspection_repository
        self._seal_repair_repository = seal_repair_repository
        self._seal_warranty_assessment_repository = seal_warranty_assessment_repository
        self._installation_report_fitment_repository = installation_report_fitment_repository

    @property
    def _seal_repos_available(self) -> bool:
        return all(
            (
                self._seal_lifecycle_event_repository,
                self._seal_inspection_repository,
                self._seal_repair_repository,
                self._seal_warranty_assessment_repository,
                self._installation_report_fitment_repository,
            )
        )

    def build(self, tag_number: str, *, knowledge: Any | None = None) -> EquipmentTimeline:
        knowledge = knowledge or self._knowledge_service.build(tag_number)

        events: list[TimelineEvent] = []
        events.extend(self._build_pm_events(knowledge.pm_history))
        events.extend(self._build_cm_events(knowledge.cm_history))
        events.extend(self._build_breakdown_events(knowledge.breakdown_history))
        events.extend(self._build_seal_replacement_events(tag_number))
        events.extend(self._build_inspection_events(knowledge.condition_monitoring_readings))
        events.extend(self._build_inventory_events(tag_number))
        events.extend(self._build_recommendation_events(tag_number))

        events_sorted = tuple(sorted(events, key=lambda event: event.occurred_at or ""))

        return EquipmentTimeline(tag_number=tag_number, events=events_sorted)

    def build_with_knowledge(self, tag_number: str, knowledge: Any) -> EquipmentTimeline:
        return self.build(tag_number, knowledge=knowledge)

    # MWO-LTSA-ASSET360-MECHANICAL-SEAL-WIRING-001 -- exposes
    # build_lifecycle()'s existing current-seal resolution (Section 3
    # priority: Seal Registry, then Installation descriptive fields, then
    # null -- see _build_current_seal's own header comment) as its own
    # small, reusable entry point, so a caller that only needs the current
    # seal (the /knowledge router) is not required to compute the entire
    # PumpLifecycle (installations, work orders, seal events, analytics)
    # just to reach it. No new derivation, no copy/paste -- both
    # _list_installations and _build_current_seal are the exact same
    # private helpers build_lifecycle() itself already calls.
    def build_current_seal(self, tag_number: str) -> PumpLifecycleCurrentSeal | None:
        installations = self._list_installations(tag_number)
        current_installation_record = installations[-1] if installations else None
        return self._build_current_seal(current_installation_record)

    def build_lifecycle(
        self,
        tag_number: str,
        *,
        today: date | None = None,
        knowledge: Any | None = None,
    ) -> PumpLifecycle:
        knowledge = knowledge or self._knowledge_service.build(tag_number)
        installations = self._list_installations(tag_number)
        work_orders = self._list_work_orders(tag_number)
        current_installation_record = installations[-1] if installations else None
        current_installation = self._map_current_installation(current_installation_record)
        current_seal = self._build_current_seal(current_installation_record)
        replacement_events = self._build_replacement_events(installations)

        # MWO-LTSA-SEAL-EQUIPMENT-HISTORY-INTEGRATION-001 -- dedup: an
        # installation_report already linked to a #6.2 INSTALL lifecycle
        # event is represented as evidence ON that new SEAL_INSTALL
        # timeline item below, never a second legacy INSTALLATION event
        # for the same real installation (this MWO's own explicit rule).
        linked_codes: frozenset[str] = (
            linked_installation_codes_for_pump(
                tag_number, installation_report_fitment_repository=self._installation_report_fitment_repository
            )
            if self._seal_repos_available
            else frozenset()
        )
        unlinked_installations = [
            record for record in installations if record.get("installation_code") not in linked_codes
        ]
        installation_events = self._build_installation_events(unlinked_installations)
        work_order_events = self._build_work_order_events(work_orders)
        failure_events = self._build_failure_events(knowledge.breakdown_history)

        seal_events: tuple[TimelineEvent, ...] = ()
        if self._seal_repos_available:
            seal_events = build_seal_events_for_pump(
                tag_number,
                seal_lifecycle_event_repository=self._seal_lifecycle_event_repository,
                seal_inspection_repository=self._seal_inspection_repository,
                seal_repair_repository=self._seal_repair_repository,
                seal_warranty_assessment_repository=self._seal_warranty_assessment_repository,
                installation_report_fitment_repository=self._installation_report_fitment_repository,
            )

        lifecycle_events: list[TimelineEvent] = []
        lifecycle_events.extend(installation_events)
        lifecycle_events.extend(self._build_pm_events(knowledge.pm_history))
        lifecycle_events.extend(self._build_cm_events(knowledge.cm_history))
        lifecycle_events.extend(self._build_inspection_events(knowledge.condition_monitoring_readings))
        lifecycle_events.extend(failure_events)
        lifecycle_events.extend(work_order_events)
        lifecycle_events.extend(replacement_events)
        lifecycle_events.extend(seal_events)
        # MWO-LTSA-067 -- lifecycle.timeline is newest-first (reverse
        # chronological), per this MWO's explicit "Order: Sort by
        # occurred_at. Newest first. No client sorting." -- the frontend
        # (PumpOpenDesignView.jsx) already renders lifecycle.timeline in
        # the order it receives, unchanged. This is deliberately distinct
        # from build()'s own `events` (used only by the older /knowledge
        # endpoint, still oldest-first, MWO-LTSA-031B/R1) -- that endpoint
        # was not part of this MWO's scope and its existing consumers/
        # tests assume oldest-first, so it is left unchanged.
        timeline = tuple(sorted(lifecycle_events, key=lambda event: event.occurred_at or "", reverse=True))

        today = today or date.today()
        elapsed_service_days = self._calculate_elapsed_service_days(current_installation_record, today=today)
        last_pm = get_pump_last_pm(
            tag_number,
            maintenance_history_gateway=self._maintenance_history_gateway,
            work_order_gateway=self._work_order_gateway,
            pm_occurrence_gateway=self._pm_occurrence_gateway,
        ).get("last_pm")
        last_cm = get_pump_last_cm(
            tag_number,
            cm_report_gateway=self._knowledge_service.cm_report_gateway,
        ).get("last_cm")
        open_work_orders = get_active_work_orders(
            tag_number,
            work_order_gateway=self._work_order_gateway,
        ).get("work_orders") or []
        next_pm = self._select_next_pm(knowledge.pm_schedules)
        last_failure = self._select_latest_failure(knowledge.breakdown_history)

        current_state = PumpLifecycleCurrentState(
            current_installation=current_installation,
            current_seal=current_seal,
            elapsed_service_days=elapsed_service_days,
            running_hours_derived=None,
            last_pm=last_pm,
            next_pm=next_pm,
            last_cm=last_cm,
            last_failure=last_failure,
            open_work_orders=open_work_orders,
        )
        analytics = PumpLifecycleAnalytics(
            elapsed_service_days=elapsed_service_days,
            pm_count=len(knowledge.pm_history),
            # MWO-LTSA-DEMO-ANALYTICS-001 -- was len(knowledge.cm_history)
            # (cm_report rows), which silently diverged from the timeline's
            # own INSPECTION category (TimelineCategory.INSPECTION, source=
            # CONDITION_MONITORING_READING), built from this exact
            # knowledge.condition_monitoring_readings list two lines above
            # (_build_inspection_events call). cm_report and condition_
            # monitoring_reading are deliberately distinct domains (ADR-
            # CONDITION-MONITORING-001, "CMON, never a bare CM") -- pm_count
            # already matched its own PM timeline category 1:1
            # (knowledge.pm_history both places); cm_count never did.
            # Reusing the same list the timeline already built from, not a
            # second query/gateway/analytics engine.
            cm_count=len(knowledge.condition_monitoring_readings),
            failure_count=len(knowledge.breakdown_history),
            mtbf=None,
            mtbr=None,
            average_seal_life=None,
            health_index=None,
            availability=None,
            reliability=None,
        )
        related_engineering = PumpLifecycleRelatedEngineering(
            pm_schedules=knowledge.pm_schedules,
            cm_reports=knowledge.cm_history,
            work_orders=work_orders,
            breakdown_history=knowledge.breakdown_history,
            drawings=knowledge.drawings,
            documents=self._list_documents(knowledge.inventory),
            inventory=knowledge.inventory,
            condition_monitoring_readings=knowledge.condition_monitoring_readings,
        )

        # MWO-LTSA-064A -- CurrentInstallation/CurrentSeal are no longer
        # constructed at the PumpLifecycle root; current_state above is
        # their one home (Section 2).
        return PumpLifecycle(
            tag_number=tag_number,
            pump=knowledge.pump,
            current_state=current_state,
            timeline=timeline,
            analytics=analytics,
            related_engineering=related_engineering,
        )

    # MWO-LTSA-064A -- Related Engineering: documents, reusing the same
    # SealEngineeringDocumentGateway instance LTSAKnowledgeService already
    # holds (self._knowledge_service.seal_engineering_document_gateway,
    # the identical reuse-an-already-constructed-gateway pattern
    # last_cm above already uses via self._knowledge_service.
    # cm_report_gateway) -- no new gateway, one list() call. Unlike
    # LTSAKnowledgeService._build_drawings(), this is not filtered to
    # document_type == 'DRAWING' -- drawings is already covered by
    # knowledge.drawings above; this is every OTHER engineering document
    # type for the same compatible seal_code(s), derived from the
    # already-computed knowledge.inventory (each row already carries its
    # own seal_code -- the same field _build_drawings() itself derives
    # compatible_seal_codes from, just read from the reshaped `inventory`
    # list here instead of the raw spare_parts list).
    def _list_documents(self, inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compatible_seal_codes = {item.get("seal_code") for item in inventory if item.get("seal_code")}
        if not compatible_seal_codes:
            return []

        gateway = self._knowledge_service.seal_engineering_document_gateway
        response = gateway.list_seal_engineering_documents()
        return [
            record
            for record in (response.get("data") or [])
            if record.get("seal_code") in compatible_seal_codes
        ]

    # -- Populated categories --------------------------------------------

    def _build_pm_events(self, records: list[dict[str, Any]]) -> tuple[TimelineEvent, ...]:
        return tuple(
            TimelineEvent(
                id=f"PM:{record.get('pm_occurrence_code')}",
                event_type=TimelineCategory.PM,
                occurred_at=record.get("occurrence_date"),
                title=f"PM Occurrence {record.get('pm_occurrence_code')}",
                description=record.get("description"),
                severity=TimelineSeverity.UNKNOWN,
                source=TimelineSource.PM_OCCURRENCE,
                derived=True,
                payload=record,
            )
            for record in records
        )

    def _build_cm_events(self, records: list[dict[str, Any]]) -> tuple[TimelineEvent, ...]:
        return tuple(
            TimelineEvent(
                id=f"CM:{record.get('cm_report_code')}",
                event_type=TimelineCategory.CM,
                occurred_at=record.get("created_at"),
                title=f"CM Report {record.get('cm_report_code')}",
                description=record.get("failure_description"),
                severity=self._parse_severity(record.get("severity")),
                source=TimelineSource.CM_REPORT,
                derived=True,
                payload=record,
            )
            for record in records
        )

    def _build_breakdown_events(self, records: list[dict[str, Any]]) -> tuple[TimelineEvent, ...]:
        return tuple(
            TimelineEvent(
                id=f"BREAKDOWN:{record.get('maintenance_record_code')}",
                event_type=TimelineCategory.BREAKDOWN,
                occurred_at=record.get("performed_at"),
                title=f"Breakdown {record.get('maintenance_record_code')}",
                description=record.get("action_taken"),
                severity=TimelineSeverity.UNKNOWN,
                source=TimelineSource.MAINTENANCE_HISTORY,
                derived=True,
                payload=record,
            )
            for record in records
        )

    def _build_failure_events(self, records: list[dict[str, Any]]) -> tuple[TimelineEvent, ...]:
        return tuple(
            TimelineEvent(
                id=f"FAILURE:{record.get('maintenance_record_code')}",
                event_type=TimelineCategory.FAILURE,
                occurred_at=record.get("performed_at"),
                title=f"Failure {record.get('maintenance_record_code')}",
                description=record.get("action_taken"),
                severity=TimelineSeverity.UNKNOWN,
                source=TimelineSource.MAINTENANCE_HISTORY,
                derived=True,
                payload=record,
            )
            for record in records
        )

    # MWO-LTSA-067 -- INSTALLATION payload is enriched with `engineer`
    # (reuses _derive_engineer(), MWO-LTSA-066 -- no second derivation
    # engine). installation_code/report_no/drawing_no/seal_code/report_date
    # are already native installation_report columns, already present on
    # `record` unchanged -- only `engineer` is a derived value with no raw
    # column, so it is the one field added on top of the raw record rather
    # than reshaping the whole payload.
    def _build_installation_events(self, records: list[dict[str, Any]]) -> tuple[TimelineEvent, ...]:
        return tuple(
            TimelineEvent(
                id=f"INSTALLATION:{record.get('installation_code')}",
                event_type=TimelineCategory.INSTALLATION,
                occurred_at=self._normalize_date_string(record.get("report_date")),
                title=f"Installation {record.get('installation_code')}",
                description=record.get("report_no"),
                severity=TimelineSeverity.UNKNOWN,
                source=TimelineSource.INSTALLATION_REPORT,
                derived=False,
                payload={**record, "engineer": self._derive_engineer(record)},
            )
            for record in records
        )

    def _build_work_order_events(self, records: list[dict[str, Any]]) -> tuple[TimelineEvent, ...]:
        return tuple(
            TimelineEvent(
                id=f"WORK_ORDER:{record.get('work_order_code')}",
                event_type=TimelineCategory.WORK_ORDER,
                occurred_at=self._work_order_occurred_at(record),
                title=f"Work Order {record.get('work_order_code')}",
                description=record.get("description") or record.get("title"),
                severity=TimelineSeverity.UNKNOWN,
                source=TimelineSource.WORK_ORDER,
                derived=False,
                payload=record,
            )
            for record in records
        )

    def _build_replacement_events(self, records: list[dict[str, Any]]) -> tuple[TimelineEvent, ...]:
        events: list[TimelineEvent] = []
        for previous, current in zip(records, records[1:]):
            events.append(
                TimelineEvent(
                    id=f"REPLACEMENT:{previous.get('installation_code')}->{current.get('installation_code')}",
                    event_type=TimelineCategory.REPLACEMENT,
                    occurred_at=self._normalize_date_string(current.get("report_date")),
                    title=f"Replacement {previous.get('installation_code')} -> {current.get('installation_code')}",
                    description=current.get("report_no"),
                    severity=TimelineSeverity.UNKNOWN,
                    source=TimelineSource.INSTALLATION_REPORT,
                    derived=True,
                    payload={
                        "replaced_installation_code": previous.get("installation_code"),
                        "replacement_installation_code": current.get("installation_code"),
                        "pump_tag_number": current.get("plant_equip_no"),
                    },
                )
            )
        return tuple(events)

    @staticmethod
    def _parse_severity(value: Any) -> TimelineSeverity:
        try:
            return TimelineSeverity(value)
        except ValueError:
            return TimelineSeverity.UNKNOWN

    # -- Canonical categories with no populated data today ----------------
    # Each always returns a tuple, never None (Chief Architect decision,
    # MWO-LTSA-031B-R1 Section 4). No heuristic, no fabricated event.

    def _build_seal_replacement_events(self, tag_number: str) -> tuple[TimelineEvent, ...]:
        return ()

    def _build_inspection_events(self, records: list[dict[str, Any]]) -> tuple[TimelineEvent, ...]:
        # MWO-LTSA-PM-CM-INTAKE-001 -- Condition Monitoring readings
        # (condition_monitoring_reading, "CMON" -- deliberately not
        # cm_report/TimelineCategory.CM, see ADR-CONDITION-MONITORING-001
        # and this MWO's own domain-correction discussion). Same shape as
        # _build_pm_events/_build_cm_events above: real records only,
        # never fabricated.
        return tuple(
            TimelineEvent(
                id=f"INSPECTION:{record.get('condition_monitoring_reading_code')}",
                event_type=TimelineCategory.INSPECTION,
                occurred_at=record.get("reading_date"),
                title=f"Condition Monitoring {record.get('condition_monitoring_reading_code')}",
                description=record.get("finding"),
                severity=TimelineSeverity.UNKNOWN,
                source=TimelineSource.CONDITION_MONITORING_READING,
                derived=True,
                payload=record,
            )
            for record in records
        )

    def _build_inventory_events(self, tag_number: str) -> tuple[TimelineEvent, ...]:
        return ()

    def _build_recommendation_events(self, tag_number: str) -> tuple[TimelineEvent, ...]:
        return ()

    def _list_installations(self, tag_number: str) -> list[dict[str, Any]]:
        response = self._installation_gateway.list_installations()
        filtered = [
            record for record in (response.get("data") or []) if record.get("plant_equip_no") == tag_number
        ]
        return sorted(filtered, key=lambda record: self._sort_key(record.get("report_date")))

    def _list_work_orders(self, tag_number: str) -> list[dict[str, Any]]:
        response = self._work_order_gateway.list_work_orders()
        filtered = [
            record for record in (response.get("data") or []) if record.get("asset_code") == tag_number
        ]
        return sorted(filtered, key=lambda record: self._sort_key(self._work_order_occurred_at(record)))

    # MWO-LTSA-064A -- Canonical CurrentSeal resolution priority (Section 3):
    #   1. Seal Registry (installation.seal_code -> seal_gateway.list_seals())
    #   2. Installation descriptive fields (seal_manufacture/seal_size/
    #      material_code) -- fallback ONLY, used exclusively for the three
    #      fields that have no Seal Registry equivalent gap-filled: a
    #      confirmed seal_registry row is never overwritten by installation
    #      data, so every field-level fallback below uses an explicit
    #      `is not None` check (never a truthy `or`, which would have
    #      incorrectly discarded a real-but-falsy Seal Registry value, e.g.
    #      an empty-but-present string).
    #   3. null -- when neither source has a value (or there is no
    #      installation at all, handled by the early return below).
    # model/temperature_limit/pressure_limit/status/seal_name have no
    # installation-side equivalent column anywhere in installation_report
    # (confirmed, MWO-LTSA-062 archaeology) -- Seal Registry or null only,
    # never a guessed fallback.
    def _build_current_seal(self, current_installation: dict[str, Any] | None) -> PumpLifecycleCurrentSeal | None:
        if current_installation is None:
            return None

        seal_code = current_installation.get("seal_code")
        seal_record: dict[str, Any] = {}
        if seal_code:
            response = self._seal_gateway.list_seals()
            seal_record = next(
                (record for record in (response.get("data") or []) if record.get("seal_code") == seal_code),
                None,
            ) or {}

        def registry_then_installation(registry_field: str, installation_field: str) -> Any:
            registry_value = seal_record.get(registry_field)
            if registry_value is not None:
                return registry_value
            return current_installation.get(installation_field)

        return PumpLifecycleCurrentSeal(
            seal_code=seal_code,
            seal_name=seal_record.get("seal_name"),
            manufacturer=registry_then_installation("manufacturer", "seal_manufacture"),
            model=seal_record.get("model"),
            shaft_size=registry_then_installation("shaft_size", "seal_size"),
            material=registry_then_installation("material", "material_code"),
            temperature_limit=seal_record.get("temperature_limit"),
            pressure_limit=seal_record.get("pressure_limit"),
            status=seal_record.get("status"),
            installation_code=current_installation.get("installation_code"),
            installed_at=self._normalize_date_string(current_installation.get("report_date")),
            source="seal_registry" if seal_record else "installation_report",
        )

    def _map_current_installation(
        self, current_installation: dict[str, Any] | None
    ) -> PumpLifecycleCurrentInstallation | None:
        if current_installation is None:
            return None

        return PumpLifecycleCurrentInstallation(
            installation_code=current_installation.get("installation_code"),
            report_no=current_installation.get("report_no"),
            report_date=self._normalize_date_string(current_installation.get("report_date")),
            plant_equip_no=current_installation.get("plant_equip_no"),
            seal_code=current_installation.get("seal_code"),
            seal_type=current_installation.get("seal_type"),
            seal_manufacture=current_installation.get("seal_manufacture"),
            drawing_no=current_installation.get("drawing_no"),
            source_document_name=current_installation.get("source_document_name"),
            engineer=self._derive_engineer(current_installation),
        )

    # MWO-LTSA-066 -- Engineer has no dedicated installation_report column;
    # installation_report.signatures (JSONB) is the one real source
    # (sampleInstallations.js's own literal transcription of the real
    # signed report -- BP-INSTALLATION's seed source -- shows
    # {id, company, name, title, date} per signatory, several roles per
    # report, e.g. "Service", "Service Engineer", "Jr. Eng / RE Insp").
    # Derived, not fabricated: the first signatory whose own real `title`
    # text contains "eng" (case-insensitive, matches "Engineer"/"Eng")
    # is reported -- no signatory is invented, no role is guessed beyond
    # a substring match on data already on the record. name is preferred;
    # title is the fallback when name is null (the real source document
    # has at least one illegible/blank signatory name). None when no
    # signatory's title mentions an engineering role at all.
    @staticmethod
    def _derive_engineer(current_installation: dict[str, Any]) -> str | None:
        signatures = current_installation.get("signatures")
        if not isinstance(signatures, list):
            return None

        for signatory in signatures:
            if not isinstance(signatory, dict):
                continue
            title = signatory.get("title")
            if title and "eng" in str(title).lower():
                return signatory.get("name") or title

        return None

    def _select_next_pm(self, pm_schedules: list[dict[str, Any]]) -> dict[str, Any] | None:
        dated = [
            schedule
            for schedule in pm_schedules
            if self._normalize_date_string(schedule.get("next_due")) is not None
        ]
        if not dated:
            return None
        return sorted(dated, key=lambda schedule: self._sort_key(schedule.get("next_due")))[0]

    def _select_latest_failure(self, breakdown_history: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not breakdown_history:
            return None
        return sorted(
            breakdown_history,
            key=lambda record: self._sort_key(record.get("performed_at")),
            reverse=True,
        )[0]

    def _calculate_elapsed_service_days(self, current_installation: dict[str, Any] | None, *, today: date) -> int | None:
        if current_installation is None:
            return None
        start = self._parse_date(current_installation.get("report_date"))
        if start is None:
            return None
        return (today - start).days

    @staticmethod
    def _work_order_occurred_at(record: dict[str, Any]) -> str | None:
        for field in ("created_at", "reported_at", "due_date", "scheduled_date", "updated_at", "closed_at"):
            if record.get(field):
                return str(record.get(field))
        return None

    @classmethod
    def _sort_key(cls, raw: Any) -> str:
        normalized = cls._normalize_date_string(raw)
        return normalized or ""

    @classmethod
    def _normalize_date_string(cls, raw: Any) -> str | None:
        parsed = cls._parse_date(raw)
        return parsed.isoformat() if parsed is not None else (str(raw)[:10] if raw else None)

    @staticmethod
    def _parse_date(raw: Any) -> date | None:
        if raw is None:
            return None
        value = str(raw).strip()
        if not value:
            return None

        iso_candidate = value[:10]
        try:
            return date.fromisoformat(iso_candidate)
        except ValueError:
            pass

        for fmt in ("%B %d, %Y", "%b %d, %Y", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        return None


__all__ = ["EquipmentTimeline", "EquipmentTimelineService", "TimelineEvent"]
