"""MWO-LTSA-SEAL-WARRANTY-ASSESSMENT-001 -- router-level proof for the
four warranty routes: route shape, actor-spoof prevention, write-
permission matrix, pump-area scoped reads (derived from the linked
INSTALL event, never seal_unit.current_pump). Same FakeRunner-injected-
via-get_import_database_runner pattern established in
test_seal_router.py/test_seal_inspection_repair_router.py --
create_warranty_assessment() issues several sequential query_scalar()
calls (unit lookup, installation-event lookup, optional inspection
lookup, then the guarded insert), so its fake returns a canned response
per call in order; decide_assessment() issues exactly one, same shape as
#6.2/#6.3's own create functions.
"""

import json
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
    get_import_database_runner,
    get_pump_gateway,
    get_seal_unit_repository,
    get_seal_warranty_assessment_repository,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity

client = TestClient(app)

_VALID_SEAL_UNIT_ID = "11111111-1111-4111-8111-111111111111"
_VALID_INSTALL_EVENT_ID = "77777777-7777-4777-8777-777777777777"
_VALID_ASSESSMENT_ID = "88888888-8888-4888-8888-888888888888"
_VALID_INSPECTION_ID = "55555555-5555-4555-8555-555555555555"


def _identity(
    role: str, user_id: str = "actor-1", *, data_scope_type: str | None = None, data_scope_value: str | None = None
) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


_SUPERUSER_IDENTITY = _identity("SUPERUSER")


class FakeSealUnitRepository:
    def __init__(self, *, units=None):
        self.units = units if units is not None else []

    def find_by_id(self, seal_unit_id):
        for unit in self.units:
            if unit["seal_unit_id"] == seal_unit_id:
                return unit
        return None


class FakeSealWarrantyAssessmentRepository:
    def __init__(self, *, assessments=None):
        self.assessments = assessments if assessments is not None else []

    def find_by_id(self, assessment_id):
        for a in self.assessments:
            if a["assessment_id"] == assessment_id:
                return a
        return None

    def list_by_seal_unit(self, seal_unit_id):
        return [a for a in self.assessments if a["seal_unit_id"] == seal_unit_id]


class FakePumpGateway:
    def __init__(self, area_by_tag):
        self.area_by_tag = area_by_tag

    def get_pump(self, tag_number):
        if tag_number not in self.area_by_tag:
            return {"success": False}
        return {"success": True, "data": {"tag_number": tag_number, "area": self.area_by_tag[tag_number]}}


class SequencedFakeRunner:
    """create_warranty_assessment() makes several sequential query_scalar()
    calls -- this fake returns one canned response per call, in order."""

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.query_scalar_calls: list[str] = []

    def query_scalar(self, sql):
        self.query_scalar_calls.append(sql)
        return self.responses.pop(0) if self.responses else "[]"


def _unit_row(seal_unit_id=_VALID_SEAL_UNIT_ID):
    return json.dumps([{"seal_unit_id": seal_unit_id}])


def _install_event_row(*, event_id=_VALID_INSTALL_EVENT_ID, seal_unit_id=_VALID_SEAL_UNIT_ID, event_type="INSTALL"):
    return json.dumps(
        [{"event_id": event_id, "seal_unit_id": seal_unit_id, "event_type": event_type, "event_at": "2026-01-01T00:00:00+00:00"}]
    )


def _inspection_row(inspection_id=_VALID_INSPECTION_ID):
    return json.dumps([{"inspection_id": inspection_id}])


def _assessment_row(**overrides):
    row = {
        "assessment_id": _VALID_ASSESSMENT_ID, "seal_unit_id": _VALID_SEAL_UNIT_ID,
        "installation_event_id": _VALID_INSTALL_EVENT_ID, "inspection_id": None, "claim_date": None,
        "failure_date": None, "installation_date": "2026-01-01T00:00:00+00:00",
        "warranty_end": "2027-07-01T00:00:00+00:00", "window_status": "INSUFFICIENT_DATA",
        "decision_status": "PENDING_EXAMINATION", "technical_reason": None, "decision_reason": None,
        "source_reference": None, "assessed_by": None, "decided_by": None, "created_by": "server-actor",
        "assessed_at": None, "decided_at": None, "created_at": "2026-01-06T00:00:00+00:00",
    }
    row.update(overrides)
    return json.dumps([row])


def _happy_create_responses(created_by="server-actor"):
    return [_unit_row(), _install_event_row(), _assessment_row(created_by=created_by)]


def _decision_outcome(
    *, assessment_found=1, pending_matched=1, inspection_matched=1, decided_by="server-actor",
):
    ok = assessment_found and pending_matched and inspection_matched
    row = {
        "assessment_id": _VALID_ASSESSMENT_ID, "seal_unit_id": _VALID_SEAL_UNIT_ID,
        "installation_event_id": _VALID_INSTALL_EVENT_ID, "inspection_id": _VALID_INSPECTION_ID,
        "claim_date": None, "failure_date": None, "installation_date": "2026-01-01T00:00:00+00:00",
        "warranty_end": "2027-07-01T00:00:00+00:00", "window_status": "WITHIN_WARRANTY_WINDOW",
        "decision_status": "ACCEPTED", "technical_reason": None, "decision_reason": "x",
        "source_reference": None, "assessed_by": None, "decided_by": decided_by, "created_by": "server-actor",
        "assessed_at": None, "decided_at": "2026-01-10T00:00:00+00:00", "created_at": "2026-01-06T00:00:00+00:00",
    }
    return json.dumps(
        {
            "assessment_found": assessment_found, "pending_matched": pending_matched,
            "inspection_matched": inspection_matched,
            "decided_json": json.dumps([row]) if ok else "[]",
        }
    )


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    yield
    app.dependency_overrides.clear()


# --- route shape -----------------------------------------------------------

def test_routes_are_registered_get_post_only_no_patch_or_delete():
    openapi = client.get("/openapi.json").json()["paths"]
    assert set(openapi["/api/ltsa/seal-units/{seal_unit_id}/warranty"]) == {"get", "post"}
    assert set(openapi["/api/ltsa/seal-warranty-assessments/{assessment_id}"]) == {"get"}
    assert set(openapi["/api/ltsa/seal-warranty-assessments/{assessment_id}/decision"]) == {"post"}
    for path in openapi:
        if "warranty" in path:
            assert "patch" not in openapi[path] and "delete" not in openapi[path]


# --- GET 404s ---------------------------------------------------------

def test_list_warranty_404s_when_seal_unit_missing():
    app.dependency_overrides[get_seal_unit_repository] = lambda: FakeSealUnitRepository(units=[])
    app.dependency_overrides[get_seal_warranty_assessment_repository] = lambda: FakeSealWarrantyAssessmentRepository()
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({})
    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/warranty")
    assert response.status_code == 404


def test_get_assessment_404s_for_unknown_id():
    app.dependency_overrides[get_seal_warranty_assessment_repository] = lambda: FakeSealWarrantyAssessmentRepository()
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({})
    response = client.get(f"/api/ltsa/seal-warranty-assessments/{_VALID_ASSESSMENT_ID}")
    assert response.status_code == 404


# --- 21: write permission matrix -------------------------------------------

def test_create_assessment_succeeds_for_superuser_and_tap_admin_only():
    for role in ("SUPERUSER", "TAP_ADMIN"):
        fake_runner = SequencedFakeRunner(_happy_create_responses())
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post(
            f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/warranty",
            json={"installation_event_id": _VALID_INSTALL_EVENT_ID},
        )
        assert response.status_code == 200, f"{role} should be authorized"


def test_create_assessment_denied_for_read_only_roles():
    for role in ("TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
        fake_runner = SequencedFakeRunner(_happy_create_responses())
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post(
            f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/warranty",
            json={"installation_event_id": _VALID_INSTALL_EVENT_ID},
        )
        assert response.status_code == 403, f"{role} must be denied"
        assert fake_runner.query_scalar_calls == []


def test_decide_assessment_succeeds_for_superuser_and_tap_admin_only():
    for role in ("SUPERUSER", "TAP_ADMIN"):
        fake_runner = SequencedFakeRunner([_decision_outcome()])
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post(
            f"/api/ltsa/seal-warranty-assessments/{_VALID_ASSESSMENT_ID}/decision",
            json={"decision": "ACCEPTED", "decision_reason": "confirmed defect"},
        )
        assert response.status_code == 200, f"{role} should be authorized"


def test_decide_assessment_denied_for_read_only_roles():
    for role in ("TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
        fake_runner = SequencedFakeRunner([_decision_outcome()])
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post(
            f"/api/ltsa/seal-warranty-assessments/{_VALID_ASSESSMENT_ID}/decision",
            json={"decision": "ACCEPTED", "decision_reason": "confirmed defect"},
        )
        assert response.status_code == 403, f"{role} must be denied"
        assert fake_runner.query_scalar_calls == []


# --- 20: actor spoof prevented ---------------------------------------------

def test_create_assessment_actor_is_always_the_authenticated_user():
    fake_runner = SequencedFakeRunner(_happy_create_responses(created_by="real-actor"))
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN", user_id="real-actor")
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner

    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/warranty",
        json={"installation_event_id": _VALID_INSTALL_EVENT_ID, "created_by": "spoofed"},
    )
    assert response.status_code == 200
    insert_sql = fake_runner.query_scalar_calls[-1]
    assert "real-actor" in insert_sql
    assert "spoofed" not in insert_sql


def test_decide_assessment_actor_is_always_the_authenticated_user():
    fake_runner = SequencedFakeRunner([_decision_outcome(decided_by="real-actor")])
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN", user_id="real-actor")
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner

    response = client.post(
        f"/api/ltsa/seal-warranty-assessments/{_VALID_ASSESSMENT_ID}/decision",
        json={"decision": "ACCEPTED", "decision_reason": "x", "decided_by": "spoofed"},
    )
    assert response.status_code == 200
    sql = fake_runner.query_scalar_calls[0]
    assert "real-actor" in sql
    assert "spoofed" not in sql


# --- error mapping -----------------------------------------------------

def test_create_assessment_maps_unknown_seal_unit_to_404():
    fake_runner = SequencedFakeRunner([json.dumps([])])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/warranty",
        json={"installation_event_id": _VALID_INSTALL_EVENT_ID},
    )
    assert response.status_code == 404


def test_create_assessment_maps_missing_installation_event_to_404():
    fake_runner = SequencedFakeRunner([_unit_row(), json.dumps([])])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/warranty",
        json={"installation_event_id": _VALID_INSTALL_EVENT_ID},
    )
    assert response.status_code == 404


# --- 15: installation event must be INSTALL ---------------------------

def test_create_assessment_maps_non_install_event_to_422():
    fake_runner = SequencedFakeRunner([_unit_row(), _install_event_row(event_type="REGISTERED")])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/warranty",
        json={"installation_event_id": _VALID_INSTALL_EVENT_ID},
    )
    assert response.status_code == 422


# --- 16: installation event must belong to same seal --------------------

def test_create_assessment_maps_mismatched_seal_unit_to_422():
    fake_runner = SequencedFakeRunner([_unit_row(), _install_event_row(seal_unit_id="99999999-9999-4999-8999-999999999999")])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/warranty",
        json={"installation_event_id": _VALID_INSTALL_EVENT_ID},
    )
    assert response.status_code == 422


def test_create_assessment_maps_invalid_chronology_to_422():
    fake_runner = SequencedFakeRunner([_unit_row(), _install_event_row()])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/warranty",
        json={"installation_event_id": _VALID_INSTALL_EVENT_ID, "failure_date": "2025-01-01T00:00:00Z"},
    )
    assert response.status_code == 422


def test_decide_assessment_maps_already_decided_to_409():
    fake_runner = SequencedFakeRunner([_decision_outcome(pending_matched=0)])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/seal-warranty-assessments/{_VALID_ASSESSMENT_ID}/decision",
        json={"decision": "ACCEPTED", "decision_reason": "x"},
    )
    assert response.status_code == 409


def test_decide_assessment_maps_missing_inspection_to_422():
    fake_runner = SequencedFakeRunner([_decision_outcome(inspection_matched=0)])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/seal-warranty-assessments/{_VALID_ASSESSMENT_ID}/decision",
        json={"decision": "ACCEPTED", "decision_reason": "x"},
    )
    assert response.status_code == 422


def test_decide_assessment_maps_missing_reason_to_422_before_touching_the_runner():
    fake_runner = SequencedFakeRunner([_decision_outcome()])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/seal-warranty-assessments/{_VALID_ASSESSMENT_ID}/decision",
        json={"decision": "ACCEPTED", "decision_reason": ""},
    )
    assert response.status_code == 422
    assert fake_runner.query_scalar_calls == []


# --- 22/23: pump-area scope from INSTALL event, never current_pump --------

def test_area_scoped_identity_sees_only_assessments_whose_install_event_pump_is_in_scope():
    assessments = [
        {"assessment_id": "a1", "seal_unit_id": _VALID_SEAL_UNIT_ID, "installation_pump_tag_number": "110-P-9A"},
        {"assessment_id": "a2", "seal_unit_id": _VALID_SEAL_UNIT_ID, "installation_pump_tag_number": "211-P-1A"},
    ]
    app.dependency_overrides[get_seal_unit_repository] = (
        lambda: FakeSealUnitRepository(units=[{"seal_unit_id": _VALID_SEAL_UNIT_ID}])
    )
    app.dependency_overrides[get_seal_warranty_assessment_repository] = (
        lambda: FakeSealWarrantyAssessmentRepository(assessments=assessments)
    )
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({"110-P-9A": "HOC", "211-P-1A": "HCC"})
    app.dependency_overrides[get_current_user] = (
        lambda: _identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC")
    )

    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/warranty")
    assert response.status_code == 200
    assert {a["assessment_id"] for a in response.json()["data"]} == {"a1"}


def test_unrestricted_role_sees_every_assessment_regardless_of_install_pump():
    assessments = [
        {"assessment_id": "b1", "seal_unit_id": _VALID_SEAL_UNIT_ID, "installation_pump_tag_number": "110-P-9A"},
        {"assessment_id": "b2", "seal_unit_id": _VALID_SEAL_UNIT_ID, "installation_pump_tag_number": "211-P-1A"},
    ]
    app.dependency_overrides[get_seal_unit_repository] = (
        lambda: FakeSealUnitRepository(units=[{"seal_unit_id": _VALID_SEAL_UNIT_ID}])
    )
    app.dependency_overrides[get_seal_warranty_assessment_repository] = (
        lambda: FakeSealWarrantyAssessmentRepository(assessments=assessments)
    )
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({"110-P-9A": "HOC", "211-P-1A": "HCC"})
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY

    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/warranty")
    assert response.status_code == 200
    assert {a["assessment_id"] for a in response.json()["data"]} == {"b1", "b2"}


# --- 27: malformed UUID clean -----------------------------------------

def test_get_assessment_malformed_id_is_a_clean_404():
    app.dependency_overrides[get_seal_warranty_assessment_repository] = lambda: FakeSealWarrantyAssessmentRepository()
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({})
    response = client.get("/api/ltsa/seal-warranty-assessments/not-a-uuid")
    assert response.status_code == 404


def test_create_assessment_malformed_seal_unit_id_is_a_clean_404():
    fake_runner = SequencedFakeRunner([])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        "/api/ltsa/seal-units/not-a-uuid/warranty",
        json={"installation_event_id": _VALID_INSTALL_EVENT_ID},
    )
    assert response.status_code == 404
    assert fake_runner.query_scalar_calls == []
