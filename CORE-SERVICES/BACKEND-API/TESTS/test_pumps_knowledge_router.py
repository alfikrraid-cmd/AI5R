import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app
from dependencies import (
    get_current_user,
    get_engineering_context_engine,
    get_equipment_timeline_service,
    get_ltsa_knowledge_service,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity
from API.equipment_timeline_service import EquipmentTimeline, TimelineEvent
from API.ltsa_knowledge_service import LTSAKnowledge
from API.recommendation_engine import Evidence, Recommendation
from API.timeline_value_objects import TimelineCategory, TimelineSeverity, TimelineSource

client = TestClient(app)

TAG = "641-P-5"

# MWO-LTSA-AUTH-001 -- this suite predates authorization and tests router-
# to-service delegation, not authorization (proven separately, per-
# permission, in TESTS/test_auth_router.py).
_SUPERUSER_IDENTITY = AuthenticatedIdentity(
    user_id="test-superuser", email="test-superuser@tap.internal",
    organization_id="test-org-tap", organization_code="TAP",
    role="TAP_ADMIN", permissions=ROLE_PERMISSIONS["TAP_ADMIN"],
)




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
        pm_schedules=[],
        condition_monitoring_schedules=[],
        condition_monitoring_readings=[],
    )
    defaults.update(overrides)
    return LTSAKnowledge(**defaults)


def _recommendation(**overrides):
    defaults = dict(
        id=f"REC_CRITICAL_CM:{TAG}",
        rule_code="REC_CRITICAL_CM",
        priority=100,
        category="INSPECTION",
        title="Immediate Inspection",
        description="An open Corrective Maintenance report with critical or major severity was found.",
        evidence=(Evidence(source="CMReport", reference="CM-1", field="severity", value="CRITICAL"),),
        confidence=1.0,
        action="Dispatch a technician for immediate inspection.",
    )
    defaults.update(overrides)
    return Recommendation(**defaults)


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
    # MWO-LTSA-AUTH-001 -- the auth override is set INSIDE this same
    # existing clear-then-restore fixture, not a second autouse fixture,
    # so ordering between the two is never ambiguous.
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
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


# MWO-LTSA-032C -- RecommendationEngine wired into LTSAKnowledgeService.
# These tests exercise only the router's serialization step (mirrors the
# existing dataclasses.asdict() pattern already used for timeline) --
# LTSAKnowledgeService's own recommendation-engine wiring is covered by
# test_ltsa_knowledge_service.py, not re-tested here.


def test_get_knowledge_recommendation_field_exists_in_response():
    _override(knowledge=_knowledge(recommendation=(_recommendation(),)))

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert "recommendation" in data


def test_get_knowledge_recommendation_serializes_empty_tuple_as_empty_list():
    _override(knowledge=_knowledge(recommendation=()))

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["recommendation"] == []


def test_get_knowledge_recommendation_serializes_populated_tuple():
    _override(knowledge=_knowledge(recommendation=(_recommendation(),)))

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert len(data["recommendation"]) == 1
    assert data["recommendation"][0]["id"] == f"REC_CRITICAL_CM:{TAG}"
    assert data["recommendation"][0]["title"] == "Immediate Inspection"


def test_get_knowledge_recommendation_preserves_priority_and_confidence():
    _override(knowledge=_knowledge(recommendation=(_recommendation(priority=90, confidence=0.75),)))

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["recommendation"][0]["priority"] == 90
    assert data["recommendation"][0]["confidence"] == 0.75


def test_get_knowledge_recommendation_preserves_evidence():
    _override(knowledge=_knowledge(recommendation=(_recommendation(),)))

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["recommendation"][0]["evidence"] == [
        {"source": "CMReport", "reference": "CM-1", "field": "severity", "value": "CRITICAL"}
    ]


# MWO-LTSA-035 -- deterministic AI Insight (EngineeringInsight), derived
# router-side from knowledge.recommendation + summary via
# build_engineering_insight(). No new derivation logic here -- mirrors the
# existing dataclasses.asdict() pass-through pattern.


def test_get_knowledge_ai_insight_field_exists_in_response():
    _override(knowledge=_knowledge(recommendation=(_recommendation(),)))

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert "ai_insight" in data


def test_get_knowledge_ai_insight_is_none_when_no_recommendations():
    _override(knowledge=_knowledge(recommendation=()))

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["ai_insight"] is None


def test_get_knowledge_ai_insight_derived_from_top_recommendation_and_summary():
    _override(
        knowledge=_knowledge(recommendation=(_recommendation(),)),
        summary={
            "asset": {"tag_number": TAG},
            "cm_summary": {"overall_condition": "CRITICAL"},
        },
    )

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["ai_insight"] == {
        "root_cause": "An open Corrective Maintenance report with critical or major severity was found.",
        "risk": "CRITICAL",
        "recommended_action": "Dispatch a technician for immediate inspection.",
        "confidence": 1.0,
    }


# MWO-LTSA-036E -- Knowledge Aggregate Extension (Asset360 Migration
# Roadmap Phase 2): pm_schedules / condition_monitoring_schedules added
# to the same GET /api/ltsa/pumps/{tag}/knowledge response -- no new
# endpoint, no second frontend fetch.


def test_get_knowledge_response_includes_pm_schedules_field():
    _override(knowledge=_knowledge(pm_schedules=[{"pm_schedule_code": "PMS-1", "asset_code": TAG}]))

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["pm_schedules"] == [{"pm_schedule_code": "PMS-1", "asset_code": TAG}]


def test_get_knowledge_response_includes_condition_monitoring_schedules_field():
    _override(
        knowledge=_knowledge(
            condition_monitoring_schedules=[{"condition_monitoring_schedule_code": "CMS-1", "asset_code": TAG}]
        )
    )

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["condition_monitoring_schedules"] == [
        {"condition_monitoring_schedule_code": "CMS-1", "asset_code": TAG}
    ]


def test_get_knowledge_new_schedule_fields_are_empty_lists_by_default():
    _override()

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["pm_schedules"] == []
    assert data["condition_monitoring_schedules"] == []


def test_get_knowledge_existing_fields_unchanged_by_this_extension():
    # Regression guard: adding two new keys must not disturb any existing
    # response field or the single-fetch shape (still exactly one "data"
    # object under one "success"/"tag_number" envelope).
    _override()

    response = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()
    data = response["data"]

    assert response["success"] is True
    assert response["tag_number"] == TAG
    assert data["seal"] == [{"seal_code": "SC-001", "part_name": "John Crane Type 21"}]
    assert data["inventory"] == [
        {"seal_code": "SC-001", "quantity_on_hand": 4, "reorder_point": 2, "location": "Warehouse A"}
    ]
    assert data["pm"] == [{"pm_occurrence_code": "PM-1", "asset_code": TAG, "occurrence_date": "2026-06-01"}]
    assert data["cm"] == [{"cm_report_code": "CM-1", "asset_code": TAG, "created_at": "2026-06-05"}]


# MWO-LTSA-036O -- Executive Metrics (MWO-LTSA-036N's compute_executive_metrics)
# wired into the same GET /api/ltsa/pumps/{tag}/knowledge response -- no new
# endpoint, no duplicate calculation, mirrors the existing ai_insight
# pass-through pattern exactly (router calls the pure function with the
# already-built LTSAKnowledge, then dataclasses.asdict() the result).


def test_get_knowledge_executive_metrics_field_exists_in_response():
    _override()

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert "executive_metrics" in data


def test_get_knowledge_executive_metrics_derived_from_the_default_fixture():
    _override()

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["executive_metrics"] == {
        "tag_number": TAG,
        "health_score": 100,
        "mtbf_days": None,
        "mttr_hours": None,
        "pm_compliance_rate": 0,
        "breakdown_count": 1,
        "critical_spare_count": 0,
    }


def test_get_knowledge_executive_metrics_health_score_reflects_recommendation_priority():
    _override(knowledge=_knowledge(recommendation=(_recommendation(priority=90),)))

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["executive_metrics"]["health_score"] == 10


def test_get_knowledge_executive_metrics_breakdown_count_matches_breakdown_field_no_duplicate_calculation():
    _override(
        knowledge=_knowledge(
            breakdown_history=[
                {"maintenance_record_code": "MH-1", "asset_code": TAG, "performed_at": "2026-06-03"},
                {"maintenance_record_code": "MH-2", "asset_code": TAG, "performed_at": "2026-06-10"},
            ]
        )
    )

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["executive_metrics"]["breakdown_count"] == len(data["breakdown"]) == 2


def test_get_knowledge_executive_metrics_critical_spare_count_from_inventory():
    _override(
        knowledge=_knowledge(
            inventory=[{"seal_code": "SC-001", "quantity_on_hand": 0, "reorder_point": 2, "location": "Warehouse A"}]
        )
    )

    data = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()["data"]

    assert data["executive_metrics"]["critical_spare_count"] == 1


def test_get_knowledge_existing_fields_unchanged_by_executive_metrics_extension():
    # Regression guard: adding executive_metrics must not disturb any
    # existing response field or the single-fetch shape.
    _override()

    response = client.get(f"/api/ltsa/pumps/{TAG}/knowledge").json()
    data = response["data"]

    assert response["success"] is True
    assert response["tag_number"] == TAG
    assert data["seal"] == [{"seal_code": "SC-001", "part_name": "John Crane Type 21"}]
    assert data["breakdown"] == [
        {"maintenance_record_code": "MH-1", "asset_code": TAG, "performed_at": "2026-06-03"}
    ]
