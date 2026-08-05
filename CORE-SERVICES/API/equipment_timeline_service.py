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

from dataclasses import dataclass
from typing import Any

from .ltsa_knowledge_service import LTSAKnowledgeService
from .timeline_value_objects import TimelineCategory, TimelineSeverity, TimelineSource


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    """Immutable canonical Timeline event -- the single event model every
    Timeline category (populated or not-yet-available) uses."""

    id: str
    event_type: TimelineCategory
    occurred_at: str | None
    title: str
    description: str | None
    severity: TimelineSeverity
    source: TimelineSource
    derived: bool
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class EquipmentTimeline:
    """Immutable: one pump's full event history, oldest first."""

    tag_number: str
    events: tuple[TimelineEvent, ...]


class EquipmentTimelineService:
    """Aggregates existing LTSA history into one chronological timeline.
    No SQL, no repository layer, no duplicated business logic -- PM, CM,
    and Breakdown filtering is never re-derived here; it is obtained
    unchanged from LTSAKnowledgeService."""

    def __init__(self, knowledge_service: LTSAKnowledgeService | None = None) -> None:
        self._knowledge_service = knowledge_service or LTSAKnowledgeService()

    def build(self, tag_number: str) -> EquipmentTimeline:
        knowledge = self._knowledge_service.build(tag_number)

        events: list[TimelineEvent] = []
        events.extend(self._build_pm_events(knowledge.pm_history))
        events.extend(self._build_cm_events(knowledge.cm_history))
        events.extend(self._build_breakdown_events(knowledge.breakdown_history))
        events.extend(self._build_seal_replacement_events(tag_number))
        events.extend(self._build_inspection_events(tag_number))
        events.extend(self._build_inventory_events(tag_number))
        events.extend(self._build_recommendation_events(tag_number))

        events_sorted = tuple(sorted(events, key=lambda event: event.occurred_at or ""))

        return EquipmentTimeline(tag_number=tag_number, events=events_sorted)

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

    def _build_inspection_events(self, tag_number: str) -> tuple[TimelineEvent, ...]:
        return ()

    def _build_inventory_events(self, tag_number: str) -> tuple[TimelineEvent, ...]:
        return ()

    def _build_recommendation_events(self, tag_number: str) -> tuple[TimelineEvent, ...]:
        return ()


__all__ = ["EquipmentTimeline", "EquipmentTimelineService", "TimelineEvent"]
