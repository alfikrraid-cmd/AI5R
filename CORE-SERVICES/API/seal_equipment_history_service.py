"""MWO-LTSA-SEAL-EQUIPMENT-HISTORY-INTEGRATION-001 -- aggregates physical
mechanical-seal history (#6.1-#6.5's own canonical tables) into
EquipmentTimelineService's existing TimelineEvent read model. Pure
aggregation/query -- no new persistence, no write path, no second
history engine. Reuses seal_unit/seal_lifecycle_event/seal_inspection/
seal_repair/seal_warranty_assessment/installation_report unmodified.

CANONICAL SOURCE OF TRUTH (never re-derived): lifecycle events remain
lifecycle truth, inspection remains inspection truth, repair remains
repair truth, warranty assessment remains warranty truth, installation
report remains evidence -- this module only reshapes already-correct
rows into TimelineEvent instances, exactly like every existing
_build_*_events() method on EquipmentTimelineService already does for
PM/CM/Breakdown.

CATEGORY MAPPING (disclosed, not exhaustive of #6.2's own 9 event
types): only INSTALL/REMOVE/RETURN_TO_STOCK/SCRAP map to their own
timeline category (SEAL_INSTALL/SEAL_REMOVE/SEAL_RETURN_TO_STOCK/
SEAL_SCRAP) -- this MWO's own CANONICAL TIMELINE list names exactly 7
categories, not all 9 #6.2 event types. REGISTERED has no pump
association and no named category, so it never appears in a pump or
seal-unit timeline (still fully present in the immutable lifecycle
ledger itself, just not re-rendered here). SEND_FOR_INSPECTION/
INSPECTION_COMPLETED/SEND_FOR_REPAIR/REPAIR_COMPLETED are lifecycle
STATE-TRANSITION markers, not the richer #6.3 engineering RECORDS --
SEAL_INSPECTION/SEAL_REPAIR timeline events are sourced directly from
seal_inspection/seal_repair (the actual findings/actions), never from
the coarser lifecycle marker events, avoiding a duplicate, less
informative rendering of the same real-world action.

ATTRIBUTION (this MWO's own CRITICAL rule): every event's pump
attribution comes from that event's OWN stored pump reference --
seal_lifecycle_event.pump_tag_number, seal_inspection.pump_tag_number,
or (for repair) the linked inspection's pump_tag_number, or (for
warranty) the linked INSTALL event's pump_tag_number -- NEVER
seal_unit.current_pump_tag_number. A repair with no linked inspection,
or a linked inspection with no pump, has no defensible historical pump
and is never fabricated into any pump's timeline (seal-unit history
still shows it).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from .timeline_value_objects import TimelineCategory, TimelineEvent, TimelineSeverity, TimelineSource

if TYPE_CHECKING:
    from .installation_fitment_service import InstallationReportFitmentRepository
    from .seal_inspection_service import SealInspectionRepository
    from .seal_lifecycle_service import SealLifecycleEventRepository
    from .seal_repair_service import SealRepairRepository
    from .seal_unit_repository import SealUnitRepository
    from .seal_warranty_service import SealWarrantyAssessmentRepository

_LIFECYCLE_EVENT_CATEGORY: dict[str, TimelineCategory] = {
    "INSTALL": TimelineCategory.SEAL_INSTALL,
    "REMOVE": TimelineCategory.SEAL_REMOVE,
    "RETURN_TO_STOCK": TimelineCategory.SEAL_RETURN_TO_STOCK,
    "SCRAP": TimelineCategory.SEAL_SCRAP,
}


def _lifecycle_events_to_timeline(
    events: list[dict[str, Any]], *, reports_by_install_event_id: dict[str, dict[str, Any]] | None = None,
) -> list[TimelineEvent]:
    reports_by_install_event_id = reports_by_install_event_id or {}
    out: list[TimelineEvent] = []
    for event in events:
        category = _LIFECYCLE_EVENT_CATEGORY.get(event.get("event_type"))
        if category is None:
            continue
        payload: dict[str, Any] = dict(event)
        if category is TimelineCategory.SEAL_INSTALL:
            # Dedup rule: a linked installation_report is evidence
            # ATTACHED to this same INSTALL timeline item, never a
            # second timeline event (this MWO's own explicit rule).
            payload["installation_report"] = reports_by_install_event_id.get(event.get("event_id"))
        out.append(
            TimelineEvent(
                id=f"{category.value}:{event.get('event_id')}",
                event_type=category,
                occurred_at=event.get("event_at"),
                title=f"{category.value.replace('_', ' ').title()} ({event.get('seal_unit_id')})",
                description=event.get("reason") or event.get("notes"),
                severity=TimelineSeverity.UNKNOWN,
                source=TimelineSource.SEAL_LIFECYCLE_EVENT,
                derived=False,
                payload=payload,
            )
        )
    return out


def _inspections_to_timeline(inspections: list[dict[str, Any]]) -> list[TimelineEvent]:
    return [
        TimelineEvent(
            id=f"SEAL_INSPECTION:{record.get('inspection_id')}",
            event_type=TimelineCategory.SEAL_INSPECTION,
            occurred_at=record.get("inspection_date"),
            title=f"Seal Inspection ({record.get('inspection_type')})",
            description=record.get("overall_condition") or record.get("recommendation"),
            severity=TimelineSeverity.UNKNOWN,
            source=TimelineSource.SEAL_INSPECTION,
            derived=False,
            payload=record,
        )
        for record in inspections
    ]


def _repairs_to_timeline(
    repairs: list[dict[str, Any]], *, pump_by_inspection_id: dict[str, str | None] | None = None,
) -> list[TimelineEvent]:
    pump_by_inspection_id = pump_by_inspection_id or {}
    events = []
    for record in repairs:
        # Derived attribution only, never stored: seal_repair itself has
        # no pump column (#6.3's own field list) -- this key exists on
        # the TIMELINE payload only, so area-scope filtering and UI
        # display both have a defensible pump when one exists (repair ->
        # inspection -> inspection.pump_tag_number), and stay correctly
        # "pumpless" (None) when it does not, never fabricated.
        derived_pump = pump_by_inspection_id.get(record.get("inspection_id"))
        # Normalized cross-cutting key every seal timeline payload carries
        # (lifecycle/inspection already have a real pump_tag_number
        # column; repair does not, so this ADDS the derived value under
        # the same key name -- one consistent field the router's scope
        # filter and the UI can both rely on regardless of source table).
        payload = {**record, "pump_tag_number": derived_pump}
        events.append(
            TimelineEvent(
                id=f"SEAL_REPAIR:{record.get('repair_id')}",
                event_type=TimelineCategory.SEAL_REPAIR,
                occurred_at=record.get("repair_date"),
                title=f"Seal Repair ({record.get('repair_type')})",
                description=record.get("repair_action"),
                severity=TimelineSeverity.UNKNOWN,
                source=TimelineSource.SEAL_REPAIR,
                derived=False,
                payload=payload,
            )
        )
    return events


def _warranty_to_timeline(assessments: list[dict[str, Any]]) -> list[TimelineEvent]:
    events = []
    for record in assessments:
        # Audited (this MWO's own explicit instruction, not guessed):
        # claim_date is when the case was raised (the most meaningful
        # "occurred at" for a claim); created_at (always present) is the
        # fallback when no claim_date was recorded.
        occurred_at = record.get("claim_date") or record.get("created_at")
        # Normalized cross-cutting key (see _repairs_to_timeline's own
        # comment) -- warranty's real column is installation_pump_tag_
        # number (derived from the linked INSTALL event's own JOIN,
        # #6.4's own repository); mirrored here under pump_tag_number so
        # every seal timeline payload exposes the same attribution key.
        payload = {**record, "pump_tag_number": record.get("installation_pump_tag_number")}
        events.append(
            TimelineEvent(
                id=f"SEAL_WARRANTY:{record.get('assessment_id')}",
                event_type=TimelineCategory.SEAL_WARRANTY,
                occurred_at=occurred_at,
                # Never collapsed into one badge (this MWO's own explicit
                # rule) -- window_status/decision_status stay two distinct
                # fields on the payload, rendered separately by the UI.
                title="Seal Warranty Assessment",
                description=None,
                severity=TimelineSeverity.UNKNOWN,
                source=TimelineSource.SEAL_WARRANTY_ASSESSMENT,
                derived=False,
                payload=payload,
            )
        )
    return events


def build_seal_events_for_pump(
    pump_tag_number: str,
    *,
    seal_lifecycle_event_repository: "SealLifecycleEventRepository",
    seal_inspection_repository: "SealInspectionRepository",
    seal_repair_repository: "SealRepairRepository",
    seal_warranty_assessment_repository: "SealWarrantyAssessmentRepository",
    installation_report_fitment_repository: "InstallationReportFitmentRepository",
) -> tuple[TimelineEvent, ...]:
    """Every event here is attributed via ITS OWN stored pump reference,
    never seal_unit.current_pump_tag_number (this MWO's own CRITICAL
    rule) -- see this module's own header for the full attribution
    chain per event type."""
    lifecycle_events = seal_lifecycle_event_repository.list_by_pump(pump_tag_number)
    reports = installation_report_fitment_repository.list_by_pump(pump_tag_number)
    reports_by_install_event_id = {
        r["installation_event_id"]: r for r in reports if r.get("installation_event_id")
    }

    inspections = seal_inspection_repository.list_by_pump(pump_tag_number)
    inspection_ids = [i["inspection_id"] for i in inspections]
    repairs = seal_repair_repository.list_by_inspection_ids(inspection_ids) if inspection_ids else []
    pump_by_inspection_id = {i["inspection_id"]: pump_tag_number for i in inspections}

    warranty_assessments = seal_warranty_assessment_repository.list_by_pump(pump_tag_number)

    out: list[TimelineEvent] = []
    out.extend(_lifecycle_events_to_timeline(lifecycle_events, reports_by_install_event_id=reports_by_install_event_id))
    out.extend(_inspections_to_timeline(inspections))
    out.extend(_repairs_to_timeline(repairs, pump_by_inspection_id=pump_by_inspection_id))
    out.extend(_warranty_to_timeline(warranty_assessments))
    return tuple(out)


def linked_installation_codes_for_pump(
    pump_tag_number: str, *, installation_report_fitment_repository: "InstallationReportFitmentRepository",
) -> frozenset[str]:
    """The set of installation_code values already represented as
    evidence on a SEAL_INSTALL event for this pump -- callers building
    the legacy INSTALLATION timeline category (raw installation_report
    rows via the n8n gateway) must exclude these to prevent double-
    counting (this MWO's own explicit rule)."""
    reports = installation_report_fitment_repository.list_by_pump(pump_tag_number)
    return frozenset(r["installation_code"] for r in reports if r.get("installation_event_id"))


def build_seal_unit_history(
    seal_unit_id: str,
    *,
    seal_lifecycle_event_repository: "SealLifecycleEventRepository",
    seal_inspection_repository: "SealInspectionRepository",
    seal_repair_repository: "SealRepairRepository",
    seal_warranty_assessment_repository: "SealWarrantyAssessmentRepository",
    installation_report_fitment_repository: "InstallationReportFitmentRepository",
) -> tuple[TimelineEvent, ...]:
    """The complete cross-pump physical journey of ONE seal_unit -- not a
    new source-of-truth table, a query/aggregation capability spanning
    every pump this unit has ever been on (this MWO's own PHYSICAL SEAL
    HISTORY requirement). Includes pumpless events (e.g. a pumpless
    inspection) that would never appear in any single pump's timeline."""
    lifecycle_events = seal_lifecycle_event_repository.list_by_seal_unit(seal_unit_id)
    reports = installation_report_fitment_repository.list_by_seal_unit(seal_unit_id)
    reports_by_install_event_id = {
        r["installation_event_id"]: r for r in reports if r.get("installation_event_id")
    }

    inspections = seal_inspection_repository.list_by_seal_unit(seal_unit_id)
    inspection_ids = [i["inspection_id"] for i in inspections]
    pump_by_inspection_id = {i["inspection_id"]: i.get("pump_tag_number") for i in inspections}
    repairs = seal_repair_repository.list_by_inspection_ids(inspection_ids) if inspection_ids else []
    # A repair may exist with no linked inspection at all -- still real
    # repair history for this physical unit, included via list_by_seal_unit
    # directly (never fabricated into a pump's timeline, but always part
    # of the seal-unit's own complete history).
    all_repairs_for_unit = seal_repair_repository.list_by_seal_unit(seal_unit_id)
    seen_repair_ids = {r["repair_id"] for r in repairs}
    repairs = repairs + [r for r in all_repairs_for_unit if r["repair_id"] not in seen_repair_ids]

    warranty_assessments = seal_warranty_assessment_repository.list_by_seal_unit(seal_unit_id)

    out: list[TimelineEvent] = []
    out.extend(_lifecycle_events_to_timeline(lifecycle_events, reports_by_install_event_id=reports_by_install_event_id))
    out.extend(_inspections_to_timeline(inspections))
    out.extend(_repairs_to_timeline(repairs, pump_by_inspection_id=pump_by_inspection_id))
    out.extend(_warranty_to_timeline(warranty_assessments))
    return tuple(
        sorted(out, key=lambda event: (event.occurred_at or "", event.id))
    )


def timeline_event_to_dict(event: TimelineEvent) -> dict[str, Any]:
    return asdict(event)


__all__ = [
    "build_seal_events_for_pump",
    "build_seal_unit_history",
    "linked_installation_codes_for_pump",
    "timeline_event_to_dict",
]
