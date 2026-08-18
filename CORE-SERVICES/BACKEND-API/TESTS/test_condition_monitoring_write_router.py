"""MWO-LTSA-PM-CM-INTAKE-001 -- Condition Monitoring Reading write-route
tests. Same authorization mechanism as PM Occurrence
(test_pm_occurrence_write_router.py) -- condensed to the CMON-specific
create/measurement/technical-review paths, not a full re-run of every
already-proven authorization case."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import get_condition_monitoring_reading_repository, get_current_user  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)


def _identity(role: str, user_id: str = "actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
    )


class FakeConditionMonitoringReadingRepository:
    def __init__(self, *, existing_codes=("CMONR-1",)):
        self.existing_codes = set(existing_codes)
        self.calls: list[tuple] = []

    def create_draft(self, **kwargs):
        self.calls.append(("create_draft", kwargs))
        return {"condition_monitoring_reading_code": "CMONR-NEW", "workflow_status": "DRAFT", **kwargs}

    def update_draft(self, code, **kwargs):
        self.calls.append(("update_draft", code, kwargs))
        return None if code not in self.existing_codes else {"condition_monitoring_reading_code": code, **kwargs}

    def submit(self, code, **kwargs):
        self.calls.append(("submit", code, kwargs))
        if code not in self.existing_codes:
            return None
        return {"condition_monitoring_reading_code": code, "workflow_status": "SUBMITTED", **kwargs}

    def admin_return_for_correction(self, code, **kwargs):
        self.calls.append(("admin_return_for_correction", code, kwargs))
        if code not in self.existing_codes:
            return None
        return {"condition_monitoring_reading_code": code, "workflow_status": "RETURNED_FOR_CORRECTION", **kwargs}

    def technical_return_for_correction(self, code, **kwargs):
        self.calls.append(("technical_return_for_correction", code, kwargs))
        return None

    def technical_finalize(self, code, **kwargs):
        self.calls.append(("technical_finalize", code, kwargs))
        if code not in self.existing_codes:
            return None
        return {"condition_monitoring_reading_code": code, "workflow_status": "FINALIZED", **kwargs}


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _override(role: str, user_id: str = "actor-1", repository=None):
    fake = repository or FakeConditionMonitoringReadingRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity(role, user_id)
    app.dependency_overrides[get_condition_monitoring_reading_repository] = lambda: fake
    return fake


def test_tap_engineer_can_create_a_reading_with_real_measurements():
    fake = _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings",
        json={
            "condition_monitoring_schedule_code": "CMS-1",
            "asset_code": "G-201-01A",
            "measurements": {"suction_temp": 34.0, "mechanical_seal_leak_de": False},
        },
    )
    assert response.status_code == 200
    assert fake.calls[0][1]["measurements"]["suction_temp"] == 34.0
    assert fake.calls[0][1]["measurements"]["mechanical_seal_leak_de"] is False


def test_missing_measurement_is_null_not_zero_through_the_full_request_cycle():
    fake = _override("TAP_ENGINEER")
    client.post(
        "/api/ltsa/condition-monitoring-readings",
        json={
            "condition_monitoring_schedule_code": "CMS-1",
            "asset_code": "G-201-01A",
            "measurements": {"suction_temp": 34.0},
        },
    )
    assert fake.calls[0][1]["measurements"]["discharge_temp"] is None
    assert fake.calls[0][1]["measurements"]["vertical_vibration_de"] is None


def test_pertamina_engineer_cannot_create_a_reading():
    _override("PERTAMINA_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings",
        json={"condition_monitoring_schedule_code": "CMS-1", "asset_code": "G-201-01A"},
    )
    assert response.status_code == 403


def test_anonymous_create_is_401():
    app.dependency_overrides.clear()
    response = client.post(
        "/api/ltsa/condition-monitoring-readings",
        json={"condition_monitoring_schedule_code": "CMS-1", "asset_code": "G-201-01A"},
    )
    assert response.status_code == 401


def test_created_by_is_always_the_authenticated_actor():
    fake = _override("TAP_ENGINEER", user_id="real-actor")
    client.post(
        "/api/ltsa/condition-monitoring-readings",
        json={"condition_monitoring_schedule_code": "CMS-1", "asset_code": "G-201-01A", "created_by": "spoofed"},
    )
    assert fake.calls[0][1]["created_by"] == "real-actor"


def test_john_crane_engineer_can_acknowledge_a_submitted_reading():
    _override("JOHN_CRANE_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/CMONR-1/technical-review",
        json={"action": "ACKNOWLEDGE", "comment": "Within normal operating range"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["workflow_status"] == "FINALIZED"


def test_john_crane_engineer_can_technically_approve():
    _override("JOHN_CRANE_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/CMONR-1/technical-review",
        json={"action": "APPROVE", "recommendation": "Schedule seal replacement within 2 weeks"},
    )
    assert response.status_code == 200


def test_tap_engineer_cannot_technically_review():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/CMONR-1/technical-review",
        json={"action": "ACKNOWLEDGE"},
    )
    assert response.status_code == 403


def test_pertamina_viewer_cannot_technically_review():
    _override("PERTAMINA_VIEWER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/CMONR-1/technical-review",
        json={"action": "ACKNOWLEDGE"},
    )
    assert response.status_code == 403


def test_tap_admin_can_administratively_return_for_correction():
    _override("TAP_ADMIN")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/CMONR-1/admin-review",
        json={"return_reason": "Reading date is missing"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["workflow_status"] == "RETURNED_FOR_CORRECTION"


def test_submit_returns_409_for_an_unknown_reading():
    _override("TAP_ENGINEER", repository=FakeConditionMonitoringReadingRepository(existing_codes=()))
    response = client.post("/api/ltsa/condition-monitoring-readings/CMONR-MISSING/submit")
    assert response.status_code == 409
