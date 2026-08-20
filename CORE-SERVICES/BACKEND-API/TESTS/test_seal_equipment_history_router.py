"""MWO-LTSA-SEAL-EQUIPMENT-HISTORY-INTEGRATION-001 -- router-level proof
for GET /api/ltsa/seal-units/{id}/history: route shape, area-scope leak
prevention (per-event, derived from each event's own pump attribution,
never seal_unit.current_pump), pumpless-events-stay-global policy,
unrestricted-role full visibility, malformed UUID, empty state.
"""

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
    get_installation_report_fitment_repository,
    get_pump_gateway,
    get_seal_inspection_repository,
    get_seal_lifecycle_event_repository,
    get_seal_repair_repository,
    get_seal_unit_repository,
    get_seal_warranty_assessment_repository,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity

client = TestClient(app)

_VALID_SEAL_UNIT_ID = "11111111-1111-4111-8111-111111111111"

_SUPERUSER_IDENTITY = AuthenticatedIdentity(
    user_id="test-superuser", email="test-superuser@tap.internal",
    organization_id="test-org-tap", organization_code="TAP",
    role="TAP_ADMIN", permissions=ROLE_PERMISSIONS["TAP_ADMIN"],
)


def _identity(
    role: str, user_id: str = "actor-1", *, data_scope_type: str | None = None, data_scope_value: str | None = None
) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


class FakeSealUnitRepository:
    def __init__(self, *, units=None):
        self.units = units if units is not None else []

    def find_by_id(self, seal_unit_id):
        for unit in self.units:
            if unit["seal_unit_id"] == seal_unit_id:
                return unit
        return None


class FakeLifecycleEventRepository:
    def __init__(self, *, events=None):
        self.events = events if events is not None else []

    def list_by_seal_unit(self, seal_unit_id):
        return [e for e in self.events if e["seal_unit_id"] == seal_unit_id]


class FakeInspectionRepository:
    def __init__(self, *, inspections=None):
        self.inspections = inspections if inspections is not None else []

    def list_by_seal_unit(self, seal_unit_id):
        return [i for i in self.inspections if i["seal_unit_id"] == seal_unit_id]


class FakeRepairRepository:
    def __init__(self, *, repairs=None):
        self.repairs = repairs if repairs is not None else []

    def list_by_seal_unit(self, seal_unit_id):
        return [r for r in self.repairs if r["seal_unit_id"] == seal_unit_id]

    def list_by_inspection_ids(self, inspection_ids):
        return [r for r in self.repairs if r.get("inspection_id") in inspection_ids]


class FakeWarrantyRepository:
    def __init__(self, *, assessments=None):
        self.assessments = assessments if assessments is not None else []

    def list_by_seal_unit(self, seal_unit_id):
        return [a for a in self.assessments if a["seal_unit_id"] == seal_unit_id]


class FakeFitmentRepository:
    def __init__(self, *, reports=None):
        self.reports = reports if reports is not None else []

    def list_by_seal_unit(self, seal_unit_id):
        return [r for r in self.reports if r.get("seal_unit_id") == seal_unit_id]

    def list_by_pump(self, pump_tag_number):
        return [r for r in self.reports if r.get("pump_tag_number") == pump_tag_number]


class FakePumpGateway:
    def __init__(self, area_by_tag):
        self.area_by_tag = area_by_tag

    def get_pump(self, tag_number):
        if tag_number not in self.area_by_tag:
            return {"success": False}
        return {"success": True, "data": {"tag_number": tag_number, "area": self.area_by_tag[tag_number]}}


def _wire(*, units=None, events=None, inspections=None, repairs=None, assessments=None, reports=None, area_by_tag=None):
    app.dependency_overrides[get_seal_unit_repository] = lambda: FakeSealUnitRepository(units=units or [])
    app.dependency_overrides[get_seal_lifecycle_event_repository] = lambda: FakeLifecycleEventRepository(events=events or [])
    app.dependency_overrides[get_seal_inspection_repository] = lambda: FakeInspectionRepository(inspections=inspections or [])
    app.dependency_overrides[get_seal_repair_repository] = lambda: FakeRepairRepository(repairs=repairs or [])
    app.dependency_overrides[get_seal_warranty_assessment_repository] = lambda: FakeWarrantyRepository(assessments=assessments or [])
    app.dependency_overrides[get_installation_report_fitment_repository] = lambda: FakeFitmentRepository(reports=reports or [])
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway(area_by_tag or {})


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    yield
    app.dependency_overrides.clear()


def _event(event_id, event_type, event_at, pump=None, **extra):
    row = {
        "event_id": event_id, "seal_unit_id": _VALID_SEAL_UNIT_ID, "event_type": event_type,
        "event_at": event_at, "pump_tag_number": pump, "reason": None, "notes": None,
    }
    row.update(extra)
    return row


def test_route_is_registered_get_only():
    openapi = client.get("/openapi.json").json()["paths"]
    assert set(openapi["/api/ltsa/seal-units/{seal_unit_id}/history"]) == {"get"}


def test_404s_for_an_unknown_seal_unit():
    _wire(units=[])
    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/history")
    assert response.status_code == 404


def test_malformed_seal_unit_id_is_a_clean_404():
    _wire(units=[])
    response = client.get("/api/ltsa/seal-units/not-a-uuid/history")
    assert response.status_code == 404


# --- 24: empty seal history clean ------------------------------------------

def test_empty_history_for_a_valid_unit_with_no_events_is_200_empty():
    _wire(units=[{"seal_unit_id": _VALID_SEAL_UNIT_ID}])
    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/history")
    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 0}


# --- 19/20: cross-scope read denied; leak prevention ----------------------

def test_area_scoped_identity_sees_only_events_whose_pump_is_in_scope():
    events = [
        _event("e1", "INSTALL", "2026-01-01T00:00:00Z", pump="110-P-9A"),
        _event("e2", "INSTALL", "2026-03-01T00:00:00Z", pump="211-P-1A"),
    ]
    _wire(
        units=[{"seal_unit_id": _VALID_SEAL_UNIT_ID}], events=events,
        area_by_tag={"110-P-9A": "HOC", "211-P-1A": "HCC"},
    )
    app.dependency_overrides[get_current_user] = lambda: _identity(
        "PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"
    )

    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/history")
    assert response.status_code == 200
    ids = {e["id"] for e in response.json()["data"]}
    assert ids == {"SEAL_INSTALL:e1"}


def test_pumpless_events_remain_globally_visible_for_a_scoped_identity():
    events = [
        _event("e1", "INSTALL", "2026-01-01T00:00:00Z", pump="211-P-1A"),  # out of scope
    ]
    inspections = [
        {"inspection_id": "i1", "seal_unit_id": _VALID_SEAL_UNIT_ID, "inspection_date": "2026-02-01T00:00:00Z", "pump_tag_number": None, "inspection_type": "GENERAL"},
    ]
    _wire(
        units=[{"seal_unit_id": _VALID_SEAL_UNIT_ID}], events=events, inspections=inspections,
        area_by_tag={"211-P-1A": "HCC"},
    )
    app.dependency_overrides[get_current_user] = lambda: _identity(
        "PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"
    )

    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/history")
    assert response.status_code == 200
    ids = {e["id"] for e in response.json()["data"]}
    assert ids == {"SEAL_INSPECTION:i1"}


# --- 22: unrestricted role sees full history -------------------------------

def test_unrestricted_role_sees_full_history_across_every_pump():
    events = [
        _event("e1", "INSTALL", "2026-01-01T00:00:00Z", pump="110-P-9A"),
        _event("e2", "INSTALL", "2026-03-01T00:00:00Z", pump="211-P-1A"),
    ]
    _wire(
        units=[{"seal_unit_id": _VALID_SEAL_UNIT_ID}], events=events,
        area_by_tag={"110-P-9A": "HOC", "211-P-1A": "HCC"},
    )
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY

    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/history")
    assert response.status_code == 200
    assert response.json()["count"] == 2
