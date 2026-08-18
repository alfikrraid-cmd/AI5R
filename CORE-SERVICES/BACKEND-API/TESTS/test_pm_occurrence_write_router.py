"""MWO-LTSA-PM-CM-INTAKE-001 -- PM Occurrence write-route tests: create/
update/submit/admin-review/technical-review authorization, actor
spoofing prevention, workflow-gate 409s."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import get_current_user, get_pm_occurrence_repository  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)


def _identity(role: str, user_id: str = "actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
    )


class FakePMOccurrenceRepository:
    def __init__(self, *, existing_codes=("PMOCC-1",)):
        self.existing_codes = set(existing_codes)
        self.calls: list[tuple] = []

    def create_draft(self, **kwargs):
        self.calls.append(("create_draft", kwargs))
        return {"pm_occurrence_code": "PMOCC-NEW", "workflow_status": "DRAFT", **kwargs}

    def update_draft(self, code, **kwargs):
        self.calls.append(("update_draft", code, kwargs))
        if code not in self.existing_codes:
            return None
        return {"pm_occurrence_code": code, "workflow_status": "DRAFT", **kwargs}

    def submit(self, code, **kwargs):
        self.calls.append(("submit", code, kwargs))
        if code not in self.existing_codes:
            return None
        return {"pm_occurrence_code": code, "workflow_status": "SUBMITTED", **kwargs}

    def admin_return_for_correction(self, code, **kwargs):
        self.calls.append(("admin_return_for_correction", code, kwargs))
        if code not in self.existing_codes:
            return None
        return {"pm_occurrence_code": code, "workflow_status": "RETURNED_FOR_CORRECTION", **kwargs}

    def technical_return_for_correction(self, code, **kwargs):
        self.calls.append(("technical_return_for_correction", code, kwargs))
        if code not in self.existing_codes:
            return None
        return {"pm_occurrence_code": code, "workflow_status": "RETURNED_FOR_CORRECTION", **kwargs}

    def technical_finalize(self, code, **kwargs):
        self.calls.append(("technical_finalize", code, kwargs))
        if code not in self.existing_codes:
            return None
        return {"pm_occurrence_code": code, "workflow_status": "FINALIZED", **kwargs}


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _override(role: str, user_id: str = "actor-1", repository=None):
    fake = repository or FakePMOccurrenceRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity(role, user_id)
    app.dependency_overrides[get_pm_occurrence_repository] = lambda: fake
    return fake


# --- create -----------------------------------------------------------


def test_tap_engineer_can_create_a_pm_occurrence():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-occurrences",
        json={"pm_schedule_code": "PMS-1", "asset_code": "211-P-18A"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["workflow_status"] == "DRAFT"


def test_pertamina_engineer_cannot_create_a_pm_occurrence():
    _override("PERTAMINA_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-occurrences",
        json={"pm_schedule_code": "PMS-1", "asset_code": "211-P-18A"},
    )
    assert response.status_code == 403


def test_pertamina_viewer_cannot_create_a_pm_occurrence():
    _override("PERTAMINA_VIEWER")
    response = client.post(
        "/api/ltsa/pm-occurrences",
        json={"pm_schedule_code": "PMS-1", "asset_code": "211-P-18A"},
    )
    assert response.status_code == 403


def test_john_crane_engineer_cannot_create_a_pm_occurrence():
    # JC is a technical review authority, not a field recorder (Phase 13's
    # own "cannot alter original field measurements as though they were
    # the TAP recorder").
    _override("JOHN_CRANE_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-occurrences",
        json={"pm_schedule_code": "PMS-1", "asset_code": "211-P-18A"},
    )
    assert response.status_code == 403


def test_anonymous_create_is_401():
    app.dependency_overrides.clear()
    response = client.post(
        "/api/ltsa/pm-occurrences",
        json={"pm_schedule_code": "PMS-1", "asset_code": "211-P-18A"},
    )
    assert response.status_code == 401


def test_created_by_is_always_the_authenticated_actor_never_the_request_body():
    fake = _override("TAP_ENGINEER", user_id="real-actor")
    client.post(
        "/api/ltsa/pm-occurrences",
        json={"pm_schedule_code": "PMS-1", "asset_code": "211-P-18A", "created_by": "spoofed-actor"},
    )
    assert fake.calls[0][1]["created_by"] == "real-actor"


# --- update draft -------------------------------------------------------


def test_tap_engineer_can_update_a_draft():
    _override("TAP_ENGINEER")
    response = client.patch("/api/ltsa/pm-occurrences/PMOCC-1", json={"finding": "OK, no findings"})
    assert response.status_code == 200


def test_updated_by_is_always_the_authenticated_actor():
    fake = _override("TAP_ENGINEER", user_id="real-actor")
    client.patch(
        "/api/ltsa/pm-occurrences/PMOCC-1",
        json={"finding": "OK", "updated_by": "spoofed-actor"},
    )
    assert fake.calls[0][2]["updated_by"] == "real-actor"


def test_update_returns_409_when_record_not_editable_or_missing():
    _override("TAP_ENGINEER", repository=FakePMOccurrenceRepository(existing_codes=()))
    response = client.patch("/api/ltsa/pm-occurrences/PMOCC-MISSING", json={"finding": "x"})
    assert response.status_code == 409


# --- submit ---------------------------------------------------------------


def test_tap_engineer_can_submit():
    _override("TAP_ENGINEER")
    response = client.post("/api/ltsa/pm-occurrences/PMOCC-1/submit")
    assert response.status_code == 200
    assert response.json()["data"]["workflow_status"] == "SUBMITTED"


def test_submit_returns_409_when_not_in_an_editable_state():
    _override("TAP_ENGINEER", repository=FakePMOccurrenceRepository(existing_codes=()))
    response = client.post("/api/ltsa/pm-occurrences/PMOCC-1/submit")
    assert response.status_code == 409


# --- TAP administrative review --------------------------------------------


def test_tap_admin_can_return_for_correction():
    _override("TAP_ADMIN")
    response = client.post(
        "/api/ltsa/pm-occurrences/PMOCC-1/admin-review",
        json={"return_reason": "Missing evidence photo"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["workflow_status"] == "RETURNED_FOR_CORRECTION"


def test_tap_engineer_cannot_perform_admin_review():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-occurrences/PMOCC-1/admin-review",
        json={"return_reason": "x"},
    )
    assert response.status_code == 403


def test_john_crane_engineer_cannot_perform_admin_review():
    _override("JOHN_CRANE_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-occurrences/PMOCC-1/admin-review",
        json={"return_reason": "x"},
    )
    assert response.status_code == 403


# --- John Crane technical review ------------------------------------------


def test_john_crane_engineer_can_technically_approve():
    _override("JOHN_CRANE_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-occurrences/PMOCC-1/technical-review",
        json={"action": "APPROVE", "recommendation": "Continue at current interval"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["workflow_status"] == "FINALIZED"


def test_john_crane_engineer_can_acknowledge():
    _override("JOHN_CRANE_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-occurrences/PMOCC-1/technical-review",
        json={"action": "ACKNOWLEDGE"},
    )
    assert response.status_code == 200


def test_john_crane_engineer_can_return_for_technical_correction():
    _override("JOHN_CRANE_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-occurrences/PMOCC-1/technical-review",
        json={"action": "RETURN", "comment": "Re-check flushing line photo"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["workflow_status"] == "RETURNED_FOR_CORRECTION"


def test_tap_admin_cannot_technically_approve_its_own_teams_work():
    # Phase 13/Hard Rule 18: JC's technical review is an authority
    # independent of TAP's own chain -- TAP_ADMIN never gets
    # maintenance.technical_review.
    _override("TAP_ADMIN")
    response = client.post(
        "/api/ltsa/pm-occurrences/PMOCC-1/technical-review",
        json={"action": "APPROVE"},
    )
    assert response.status_code == 403


def test_tap_engineer_cannot_technically_review_its_own_submission():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-occurrences/PMOCC-1/technical-review",
        json={"action": "APPROVE"},
    )
    assert response.status_code == 403


def test_pertamina_engineer_cannot_technically_review():
    _override("PERTAMINA_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-occurrences/PMOCC-1/technical-review",
        json={"action": "APPROVE"},
    )
    assert response.status_code == 403


def test_technical_reviewer_is_always_the_authenticated_actor_never_the_request_body():
    fake = _override("JOHN_CRANE_ENGINEER", user_id="real-jc")
    client.post(
        "/api/ltsa/pm-occurrences/PMOCC-1/technical-review",
        json={"action": "ACKNOWLEDGE", "technical_reviewed_by": "spoofed-jc"},
    )
    assert fake.calls[0][2]["technical_reviewed_by"] == "real-jc"
