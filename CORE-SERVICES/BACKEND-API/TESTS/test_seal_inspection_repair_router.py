"""MWO-LTSA-SEAL-INSPECTION-REPAIR-001 -- router-level proof for the six
seal inspection/repair routes: append-only route shape, actor-spoof
prevention, write-permission matrix, pump-area scoped reads, pumpless
global reads. Same FakeRunner-injected-via-get_import_database_runner
pattern test_seal_router.py's own lifecycle-route tests established --
create_inspection()/create_repair() are imported directly into the
router (not FastAPI dependencies themselves), so only their `runner`
parameter is overridable.
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
    get_seal_inspection_repository,
    get_seal_repair_repository,
    get_seal_unit_repository,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity

client = TestClient(app)

_VALID_SEAL_UNIT_ID = "11111111-1111-4111-8111-111111111111"
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


class FakeSealInspectionRepository:
    def __init__(self, *, inspections=None):
        self.inspections = inspections if inspections is not None else []

    def find_by_id(self, inspection_id):
        for i in self.inspections:
            if i["inspection_id"] == inspection_id:
                return i
        return None

    def list_by_seal_unit(self, seal_unit_id):
        return [i for i in self.inspections if i["seal_unit_id"] == seal_unit_id]

    def list_by_pump(self, pump_tag_number):
        return [i for i in self.inspections if i.get("pump_tag_number") == pump_tag_number]


class FakeSealRepairRepository:
    def __init__(self, *, repairs=None):
        self.repairs = repairs if repairs is not None else []

    def find_by_id(self, repair_id):
        for r in self.repairs:
            if r["repair_id"] == repair_id:
                return r
        return None

    def list_by_seal_unit(self, seal_unit_id):
        return [r for r in self.repairs if r["seal_unit_id"] == seal_unit_id]


class FakePumpGateway:
    def __init__(self, area_by_tag):
        self.area_by_tag = area_by_tag

    def get_pump(self, tag_number):
        if tag_number not in self.area_by_tag:
            return {"success": False}
        return {"success": True, "data": {"tag_number": tag_number, "area": self.area_by_tag[tag_number]}}


class FakeRunner:
    def __init__(self, outcome: str):
        self.outcome = outcome
        self.query_scalar_calls: list[str] = []

    def query_scalar(self, sql):
        self.query_scalar_calls.append(sql)
        return self.outcome


def _inspection_outcome(
    *, unit_found=1, status_matched=1, pump_matched=1, inspection_id=_VALID_INSPECTION_ID,
    seal_unit_id=_VALID_SEAL_UNIT_ID, created_by="server-actor",
):
    row = {
        "inspection_id": inspection_id, "seal_unit_id": seal_unit_id, "inspection_date": "2026-01-06T00:00:00+00:00",
        "pump_tag_number": None, "inspection_type": "GENERAL", "overall_condition": None, "failure_mode": None,
        "root_cause": None, "recommendation": None, "disposition": None, "inspected_by": None, "notes": None,
        "source_reference": None, "created_by": created_by, "created_at": "2026-01-06T00:00:00+00:00",
    }
    ok = unit_found and status_matched and pump_matched
    return json.dumps(
        {
            "unit_found": unit_found, "status_matched": status_matched, "pump_matched": pump_matched,
            "inspection_json": json.dumps([row]) if ok else "[]",
            "findings_json": "[]",
        }
    )


def _repair_outcome(
    *, unit_found=1, status_matched=1, inspection_matched=1, repair_id="66666666-6666-4666-8666-666666666666",
    seal_unit_id=_VALID_SEAL_UNIT_ID, created_by="server-actor",
):
    row = {
        "repair_id": repair_id, "seal_unit_id": seal_unit_id, "inspection_id": None,
        "repair_date": "2026-01-10T00:00:00+00:00", "repair_type": "OVERHAUL", "repair_action": "x",
        "parts_replaced": None, "repair_result": None, "performed_by": None, "notes": None,
        "source_reference": None, "created_by": created_by, "created_at": "2026-01-10T00:00:00+00:00",
    }
    ok = unit_found and status_matched and inspection_matched
    return json.dumps(
        {
            "unit_found": unit_found, "status_matched": status_matched, "inspection_matched": inspection_matched,
            "repair_json": json.dumps([row]) if ok else "[]",
        }
    )


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    yield
    app.dependency_overrides.clear()


# --- route shape / append-only -------------------------------------------

def test_routes_are_registered_with_no_patch_or_delete():
    openapi = client.get("/openapi.json").json()["paths"]
    assert set(openapi["/api/ltsa/seal-units/{seal_unit_id}/inspections"]) == {"get", "post"}
    assert set(openapi["/api/ltsa/seal-inspections/{inspection_id}"]) == {"get"}
    assert set(openapi["/api/ltsa/seal-units/{seal_unit_id}/repairs"]) == {"get", "post"}
    assert set(openapi["/api/ltsa/seal-repairs/{repair_id}"]) == {"get"}
    for path in openapi:
        if "inspection" in path or ("seal-units" in path and "repair" in path) or "seal-repairs" in path:
            assert "patch" not in openapi[path] and "delete" not in openapi[path]


# --- GET: 404s ---------------------------------------------------------

def test_list_inspections_404s_when_seal_unit_missing():
    app.dependency_overrides[get_seal_unit_repository] = lambda: FakeSealUnitRepository(units=[])
    app.dependency_overrides[get_seal_inspection_repository] = lambda: FakeSealInspectionRepository()
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({})

    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/inspections")
    assert response.status_code == 404


def test_list_repairs_404s_when_seal_unit_missing():
    app.dependency_overrides[get_seal_unit_repository] = lambda: FakeSealUnitRepository(units=[])
    app.dependency_overrides[get_seal_repair_repository] = lambda: FakeSealRepairRepository()

    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/repairs")
    assert response.status_code == 404


def test_get_inspection_404s_for_unknown_id():
    app.dependency_overrides[get_seal_inspection_repository] = lambda: FakeSealInspectionRepository()
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({})
    response = client.get(f"/api/ltsa/seal-inspections/{_VALID_INSPECTION_ID}")
    assert response.status_code == 404


def test_get_repair_404s_for_unknown_id():
    app.dependency_overrides[get_seal_repair_repository] = lambda: FakeSealRepairRepository()
    response = client.get("/api/ltsa/seal-repairs/66666666-6666-4666-8666-666666666666")
    assert response.status_code == 404


# --- 14: write permission matrix -----------------------------------------

def test_create_inspection_succeeds_for_superuser_and_tap_admin_only():
    for role in ("SUPERUSER", "TAP_ADMIN"):
        fake_runner = FakeRunner(_inspection_outcome())
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post(
            f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/inspections",
            json={"inspection_date": "2026-01-06T00:00:00Z", "inspection_type": "GENERAL"},
        )
        assert response.status_code == 200, f"{role} should be authorized"


def test_create_inspection_denied_for_read_only_roles():
    for role in ("TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
        fake_runner = FakeRunner(_inspection_outcome())
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post(
            f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/inspections",
            json={"inspection_date": "2026-01-06T00:00:00Z", "inspection_type": "GENERAL"},
        )
        assert response.status_code == 403, f"{role} must be denied"
        assert fake_runner.query_scalar_calls == []


def test_create_repair_succeeds_for_superuser_and_tap_admin_only():
    for role in ("SUPERUSER", "TAP_ADMIN"):
        fake_runner = FakeRunner(_repair_outcome())
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post(
            f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/repairs",
            json={"repair_date": "2026-01-10T00:00:00Z", "repair_type": "OVERHAUL", "repair_action": "x"},
        )
        assert response.status_code == 200, f"{role} should be authorized"


def test_create_repair_denied_for_read_only_roles():
    for role in ("TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
        fake_runner = FakeRunner(_repair_outcome())
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post(
            f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/repairs",
            json={"repair_date": "2026-01-10T00:00:00Z", "repair_type": "OVERHAUL", "repair_action": "x"},
        )
        assert response.status_code == 403, f"{role} must be denied"
        assert fake_runner.query_scalar_calls == []


# --- 13: actor spoof blocked -----------------------------------------------

def test_create_inspection_actor_is_always_the_authenticated_user():
    fake_runner = FakeRunner(_inspection_outcome(created_by="real-actor"))
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN", user_id="real-actor")
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner

    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/inspections",
        json={"inspection_date": "2026-01-06T00:00:00Z", "inspection_type": "GENERAL", "created_by": "spoofed"},
    )
    assert response.status_code == 200
    sql = fake_runner.query_scalar_calls[0]
    assert "real-actor" in sql
    assert "spoofed" not in sql


def test_create_repair_actor_is_always_the_authenticated_user():
    fake_runner = FakeRunner(_repair_outcome(created_by="real-actor"))
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN", user_id="real-actor")
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner

    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/repairs",
        json={
            "repair_date": "2026-01-10T00:00:00Z", "repair_type": "OVERHAUL", "repair_action": "x",
            "created_by": "spoofed",
        },
    )
    assert response.status_code == 200
    sql = fake_runner.query_scalar_calls[0]
    assert "real-actor" in sql
    assert "spoofed" not in sql


# --- error mapping -----------------------------------------------------

def test_create_inspection_maps_service_errors_to_expected_status_codes():
    cases = [
        (_inspection_outcome(unit_found=0, status_matched=0, pump_matched=0), 404),
        (_inspection_outcome(status_matched=0, pump_matched=0), 409),
        (_inspection_outcome(pump_matched=0), 422),
    ]
    for outcome, expected_status in cases:
        fake_runner = FakeRunner(outcome)
        app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post(
            f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/inspections",
            json={"inspection_date": "2026-01-06T00:00:00Z", "inspection_type": "GENERAL", "pump_tag_number": "110-P-9A"},
        )
        assert response.status_code == expected_status


def test_create_repair_maps_service_errors_to_expected_status_codes():
    cases = [
        (_repair_outcome(unit_found=0, status_matched=0, inspection_matched=0), 404),
        (_repair_outcome(status_matched=0, inspection_matched=0), 409),
        (_repair_outcome(inspection_matched=0), 422),
    ]
    for outcome, expected_status in cases:
        fake_runner = FakeRunner(outcome)
        app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post(
            f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/repairs",
            json={"repair_date": "2026-01-10T00:00:00Z", "repair_type": "OVERHAUL", "repair_action": "x"},
        )
        assert response.status_code == expected_status


def test_create_inspection_rejects_an_unknown_inspection_type_before_touching_the_runner():
    fake_runner = FakeRunner(_inspection_outcome())
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/inspections",
        json={"inspection_date": "2026-01-06T00:00:00Z", "inspection_type": "NOT_REAL"},
    )
    assert response.status_code == 422
    assert fake_runner.query_scalar_calls == []


# --- 15/16: pump-area scoped reads, pumpless global reads -----------------

def test_area_scoped_identity_sees_only_in_scope_inspection_pump_events_and_all_pumpless():
    inspections = [
        {"inspection_id": "a1", "seal_unit_id": _VALID_SEAL_UNIT_ID, "pump_tag_number": None},
        {"inspection_id": "a2", "seal_unit_id": _VALID_SEAL_UNIT_ID, "pump_tag_number": "110-P-9A"},
        {"inspection_id": "a3", "seal_unit_id": _VALID_SEAL_UNIT_ID, "pump_tag_number": "211-P-1A"},
    ]
    app.dependency_overrides[get_seal_unit_repository] = (
        lambda: FakeSealUnitRepository(units=[{"seal_unit_id": _VALID_SEAL_UNIT_ID}])
    )
    app.dependency_overrides[get_seal_inspection_repository] = (
        lambda: FakeSealInspectionRepository(inspections=inspections)
    )
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({"110-P-9A": "HOC", "211-P-1A": "HCC"})
    app.dependency_overrides[get_current_user] = (
        lambda: _identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC")
    )

    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/inspections")
    assert response.status_code == 200
    ids = {i["inspection_id"] for i in response.json()["data"]}
    assert ids == {"a1", "a2"}


def test_unrestricted_role_sees_every_inspection_regardless_of_pump_area():
    inspections = [
        {"inspection_id": "b1", "seal_unit_id": _VALID_SEAL_UNIT_ID, "pump_tag_number": "110-P-9A"},
        {"inspection_id": "b2", "seal_unit_id": _VALID_SEAL_UNIT_ID, "pump_tag_number": "211-P-1A"},
    ]
    app.dependency_overrides[get_seal_unit_repository] = (
        lambda: FakeSealUnitRepository(units=[{"seal_unit_id": _VALID_SEAL_UNIT_ID}])
    )
    app.dependency_overrides[get_seal_inspection_repository] = (
        lambda: FakeSealInspectionRepository(inspections=inspections)
    )
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({"110-P-9A": "HOC", "211-P-1A": "HCC"})
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY

    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/inspections")
    assert response.status_code == 200
    assert {i["inspection_id"] for i in response.json()["data"]} == {"b1", "b2"}


def test_repairs_are_globally_readable_under_seal_read_pumpless_by_design():
    # seal_repair has no pump_tag_number column at all (this MWO's own
    # field list) -- every repair row is pumpless, so a restricted
    # Pertamina identity must still see every repair for a seal unit it
    # can otherwise read.
    repairs = [
        {"repair_id": "c1", "seal_unit_id": _VALID_SEAL_UNIT_ID},
        {"repair_id": "c2", "seal_unit_id": _VALID_SEAL_UNIT_ID},
    ]
    app.dependency_overrides[get_seal_unit_repository] = (
        lambda: FakeSealUnitRepository(units=[{"seal_unit_id": _VALID_SEAL_UNIT_ID}])
    )
    app.dependency_overrides[get_seal_repair_repository] = lambda: FakeSealRepairRepository(repairs=repairs)
    app.dependency_overrides[get_current_user] = (
        lambda: _identity("PERTAMINA_VIEWER", data_scope_type="AREA", data_scope_value="HOC")
    )

    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/repairs")
    assert response.status_code == 200
    assert response.json()["count"] == 2


# --- malformed UUID (defense in depth at router level) --------------------

def test_get_inspection_malformed_id_is_a_clean_404():
    app.dependency_overrides[get_seal_inspection_repository] = lambda: FakeSealInspectionRepository()
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({})
    response = client.get("/api/ltsa/seal-inspections/not-a-uuid")
    assert response.status_code == 404


def test_get_repair_malformed_id_is_a_clean_404():
    app.dependency_overrides[get_seal_repair_repository] = lambda: FakeSealRepairRepository()
    response = client.get("/api/ltsa/seal-repairs/not-a-uuid")
    assert response.status_code == 404
