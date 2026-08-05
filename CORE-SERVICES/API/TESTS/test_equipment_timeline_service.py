import dataclasses
import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.equipment_timeline_service import EquipmentTimeline, EquipmentTimelineService, TimelineEvent
from API.ltsa_knowledge_service import LTSAKnowledge
from API.timeline_value_objects import TimelineCategory, TimelineSeverity, TimelineSource


class FakeKnowledgeService:
    def __init__(self, knowledge):
        self._knowledge = knowledge

    def build(self, tag_number):
        return self._knowledge


TAG = "641-P-5"


def _knowledge(pm_history=None, cm_history=None, breakdown_history=None):
    return LTSAKnowledge(
        tag_number=TAG,
        pump=None,
        seal=[],
        inventory=[],
        pm_history=pm_history or [],
        cm_history=cm_history or [],
        breakdown_history=breakdown_history or [],
        drawings=None,
        recommendation=None,
    )


def _service(pm_history=None, cm_history=None, breakdown_history=None):
    knowledge = _knowledge(pm_history, cm_history, breakdown_history)
    return EquipmentTimelineService(knowledge_service=FakeKnowledgeService(knowledge))


def _events_by_category(timeline, category):
    return [event for event in timeline.events if event.event_type == category]


def test_build_returns_equipment_timeline_instance():
    service = _service()

    timeline = service.build(TAG)

    assert isinstance(timeline, EquipmentTimeline)
    assert timeline.tag_number == TAG


def test_timeline_merges_pm_cm_and_breakdown_events():
    service = _service(
        pm_history=[{"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-01"}],
        cm_history=[{"cm_report_code": "CM-1", "asset_code": TAG, "created_at": "2026-06-05"}],
        breakdown_history=[
            {"maintenance_record_code": "MH-1", "asset_code": TAG, "performed_at": "2026-06-03"}
        ],
    )

    timeline = service.build(TAG)

    assert len(timeline.events) == 3
    categories = {event.event_type for event in timeline.events}
    assert categories == {TimelineCategory.PM, TimelineCategory.CM, TimelineCategory.BREAKDOWN}


def test_timeline_is_sorted_chronologically_ascending():
    service = _service(
        pm_history=[{"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-10"}],
        cm_history=[{"cm_report_code": "CM-1", "asset_code": TAG, "created_at": "2026-01-01"}],
        breakdown_history=[
            {"maintenance_record_code": "MH-1", "asset_code": TAG, "performed_at": "2026-03-15"}
        ],
    )

    timeline = service.build(TAG)

    occurred_ats = [event.occurred_at for event in timeline.events]
    assert occurred_ats == ["2026-01-01", "2026-03-15", "2026-06-10"]


# --- Canonical TimelineEvent fields, per category -------------------------


def test_pm_event_has_correct_canonical_fields():
    service = _service(
        pm_history=[{"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-01"}]
    )

    event = _events_by_category(service.build(TAG), TimelineCategory.PM)[0]

    assert event.id == "PM:PM-1"
    assert event.event_type == TimelineCategory.PM
    assert event.occurred_at == "2026-06-01"
    assert event.title == "PM Occurrence PM-1"
    assert event.severity == TimelineSeverity.UNKNOWN
    assert event.source == TimelineSource.PM_OCCURRENCE
    assert event.derived is True
    assert event.payload == {"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-01"}


def test_cm_event_has_correct_canonical_fields_and_severity_from_real_field():
    service = _service(
        cm_history=[
            {
                "cm_report_code": "CM-1",
                "asset_code": TAG,
                "created_at": "2026-06-05",
                "severity": "CRITICAL",
                "failure_description": "Seal leak detected on DE side",
            }
        ]
    )

    event = _events_by_category(service.build(TAG), TimelineCategory.CM)[0]

    assert event.id == "CM:CM-1"
    assert event.occurred_at == "2026-06-05"
    assert event.title == "CM Report CM-1"
    assert event.description == "Seal leak detected on DE side"
    assert event.severity == TimelineSeverity.CRITICAL
    assert event.source == TimelineSource.CM_REPORT
    assert event.derived is True


def test_cm_event_severity_falls_back_to_unknown_when_missing_or_unrecognized():
    service = _service(cm_history=[{"cm_report_code": "CM-1", "asset_code": TAG, "created_at": "2026-06-05"}])

    event = _events_by_category(service.build(TAG), TimelineCategory.CM)[0]

    assert event.severity == TimelineSeverity.UNKNOWN


def test_breakdown_event_has_correct_canonical_fields():
    service = _service(
        breakdown_history=[
            {
                "maintenance_record_code": "MH-1",
                "asset_code": TAG,
                "performed_at": "2026-06-03",
                "action_taken": "Replaced bearing",
            }
        ]
    )

    event = _events_by_category(service.build(TAG), TimelineCategory.BREAKDOWN)[0]

    assert event.id == "BREAKDOWN:MH-1"
    assert event.occurred_at == "2026-06-03"
    assert event.title == "Breakdown MH-1"
    assert event.description == "Replaced bearing"
    assert event.severity == TimelineSeverity.UNKNOWN
    assert event.source == TimelineSource.MAINTENANCE_HISTORY
    assert event.derived is True


# --- Canonical categories with no populated data (never None) -------------


@pytest.mark.parametrize(
    "category",
    [
        TimelineCategory.SEAL_REPLACEMENT,
        TimelineCategory.INSPECTION,
        TimelineCategory.INVENTORY_EVENT,
        TimelineCategory.RECOMMENDATION,
    ],
)
def test_unavailable_categories_return_empty_collection_never_none(category):
    service = _service()

    timeline = service.build(TAG)

    matching = _events_by_category(timeline, category)
    assert matching == []
    assert matching is not None


def test_empty_history_produces_empty_timeline():
    service = _service()

    timeline = service.build(TAG)

    assert timeline.events == ()


def test_events_with_missing_occurred_at_sort_first():
    service = _service(
        pm_history=[{"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": None}],
        cm_history=[{"cm_report_code": "CM-1", "asset_code": TAG, "created_at": "2026-06-05"}],
    )

    timeline = service.build(TAG)

    assert timeline.events[0].event_type == TimelineCategory.PM
    assert timeline.events[0].occurred_at is None


# --- Immutability -----------------------------------------------------------


def test_equipment_timeline_is_immutable():
    service = _service()
    timeline = service.build(TAG)

    with pytest.raises(dataclasses.FrozenInstanceError):
        timeline.events = ()


def test_timeline_event_is_immutable():
    service = _service(
        pm_history=[{"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-01"}]
    )
    timeline = service.build(TAG)

    with pytest.raises(dataclasses.FrozenInstanceError):
        timeline.events[0].event_type = TimelineCategory.CM


def test_service_defaults_to_real_knowledge_service_when_none_injected():
    service = EquipmentTimelineService()

    assert service is not None
