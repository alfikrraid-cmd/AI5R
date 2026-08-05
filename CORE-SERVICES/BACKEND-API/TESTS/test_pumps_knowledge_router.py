import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app
from dependencies import (
    get_engineering_context_engine,
    get_equipment_timeline_service,
    get_ltsa_knowledge_service,
)
from API.equipment_timeline_service import EquipmentTimeline, TimelineEvent
from API.ltsa_knowledge_service import LTSAKnowledge
from API.timeline_value_objects import TimelineCategory, TimelineSeverity, TimelineSource

client = TestClient(app)

TAG = "641-P-5"


class FakeKnowledgeService:
    def __init__(self, knowledge):
        self.knowledge = knowledge
        self.calls = []

    def build(self, tag_number):
        self.calls.append(tag_number)
        return self.knowledge


class FakeTimelineService:
    def __init__(self, timeline):
        self.timeline = timeline
        self.calls = []

    def build(self, tag_number):
        self.calls.append(tag_number)
        return self.timeline


class FakeContextEngine:
    def __init__(self, summary):
        self.summary = summary
        self.calls = []

    def build(self, tag_number):
        self.calls.append(tag_number)
        return self.summary


def _knowledge(**overrides):
    defaults = dict(
        tag_number=TAG,
        pump={"tag_number": TAG, "pump_name": "Main Feed Pump"},
        seal=[{"seal_code": "SC-001", "part_name": "John Crane Type 21"}],
        inventory=[{"seal_code": "SC-001", "quantity_on_hand": 4, "reorder_point": 2, "location": "Warehouse A"}],
        pm_history=[{"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-01"}],
        cm_history=[{"cm_report_code": "CM-1", "asset_code": TAG, "created_at": "2026-06-05"}],
        breakdown_history=[{"maintenance_record_code": "MH-1", "asset_code": TAG, "performed_at": "2026-06-03"}],
        drawings=None,
        recommendation=None,
    )
    defaults.update(overrides)
    return LTSAKnowledge(**defaults)


def _timeline():
    event = TimelineEvent(
        id="PM:PM-1",
        event_type=TimelineCategory.PM,
        occurred_at="2026-06-01",
        title="PM Occurrence PM-1",
        description=None,
        severity=TimelineSeverity.UNKNOWN,
        source=TimelineSource.PM_OCCURRENCE,
        derived=True,
        payload={"pm_occurrence_code": "PM-1"},
    )
    return EquipmentTimeline(tag_number=TAG, events=(event,))


def _summary():
    return {"asset": {"tag_number": TAG}, "pm_summary": {"status": "ACTIVE"}}


def _override(knowledge=None, timeline=None, summary=None):
    knowledge_fake = FakeKnowledgeService(knowledge if knowledge is not None else _knowledge())
    timeline_fake = FakeTimelineService(timeline if timeline is not None else _timeline())
    summary_fake = FakeContextEngine(summary if summary is not None else _summary())

    app.dependency_overrides[get_ltsa_knowledge_service] = lambda: knowledge_fake
    app.dependency_overrides[get_equipment_timeline_service] = lambda: timeline_fake
    app.dependency_overrides[get_engineering_context_engine] = lambda: summary_fake

    return knowledge_fake, timeline_fake, summary_fake


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_knowledge_route_is_registered():
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/ltsa/pumps/{tag}/knowledge" in paths


def test_knowledge_route_allows_only_get():
    methods = client.get("/openapi.json").json()["paths"]["/api/ltsa/pumps/{tag}/knowledge"]

    assert set(methods) == {"get"}


def test_get_knowledge_returns_200():
    _override()

    response = client.get(f"/api/ltsa/pumps/{TAG}/knowledge")

    assert response.status_code == 200


def test_get_knowledge_invokes_all_three_services_with_the_tag():
    knowledge_fake, timeline_fake, summary_fake = _override()

    client.get(f"/api/ltsa/pumps/{TAG}/knowledge")

    assert knowledge_fake.calls == [TAG]
    assert timeline_fake.calls == [TAG]
    assert summary_fake.calls == [TAG]


def test_get_knowledge_seal_inventory_pm_cm_breakdown_come_from_knowledge_service():
    _override()

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["seal"] == [{"seal_code": "SC-001", "part_name": "John Crane Type 21"}]
    assert data["inventory"] == [
        {"seal_code": "SC-001", "quantity_on_hand": 4, "reorder_point": 2, "location": "Warehouse A"}
    ]
    assert data["pm"] == [{"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-01"}]
    assert data["cm"] == [{"cm_report_code": "CM-1", "asset_code": TAG, "created_at": "2026-06-05"}]
    assert data["breakdown"] == [
        {"maintenance_record_code": "MH-1", "asset_code": TAG, "performed_at": "2026-06-03"}
    ]


def test_get_knowledge_timeline_comes_from_timeline_service():
    _override()

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["timeline"] == [
        {
            "id": "PM:PM-1",
            "event_type": "PM",
            "occurred_at": "2026-06-01",
            "title": "PM Occurrence PM-1",
            "description": None,
            "severity": "UNKNOWN",
            "source": "PM_OCCURRENCE",
            "derived": True,
            "payload": {"pm_occurrence_code": "PM-1"},
        }
    ]


def test_get_knowledge_summary_comes_from_context_engine():
    _override()

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["summary"] == {"asset": {"tag_number": TAG}, "pm_summary": {"status": "ACTIVE"}}


def test_get_knowledge_drawings_and_recommendation_are_none_when_unavailable():
    _override(knowledge=_knowledge(drawings=None, recommendation=None))

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["drawings"] is None
    assert data["recommendation"] is None


def test_get_knowledge_preserves_tag_number_in_response():
    _override()

    response = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()

    assert response["tag_number"] == TAG
    assert response["success"] is True
