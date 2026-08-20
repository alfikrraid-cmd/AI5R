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
    get_installation_gateway,
    get_installation_report_fitment_repository,
    get_pump_gateway,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity

client = TestClient(app)

# MWO-LTSA-AUTH-001 -- see test_pumps_knowledge_router.py's identical fixture.
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



# MWO-LTSA-060 -- Installation Report production persistence path. Router
# only: no filtering, no derivation, no business logic here -- each
# InstallationGateway result is returned unchanged, mirroring
# pm_schedule.py's list/detail pass-through exactly.


class FakeInstallationGateway:
    def __init__(self, list_response=None, detail_response=None):
        self.list_response = list_response
        self.detail_response = detail_response
        self.list_calls = 0
        self.detail_calls = []

    def list_installations(self):
        self.list_calls += 1
        return self.list_response

    def get_installation(self, installation_code):
        self.detail_calls.append(installation_code)
        return self.detail_response


def _response(data):
    return {"success": True, "message": "ok", "data": data}


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    # MWO-LTSA-AUTH-001 -- see test_pumps_knowledge_router.py's identical fixture.
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    yield
    app.dependency_overrides.clear()


def test_installations_list_route_is_registered():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/ltsa/installations" in paths


def test_installations_detail_route_is_registered():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/ltsa/installations/{installation_code}" in paths


def test_both_routes_allow_only_get():
    openapi = client.get("/openapi.json").json()["paths"]
    assert set(openapi["/api/ltsa/installations"]) == {"get"}
    assert set(openapi["/api/ltsa/installations/{installation_code}"]) == {"get"}


def test_list_installations_returns_the_gateways_response_unchanged():
    fake = FakeInstallationGateway(
        list_response=_response([{"installation_code": "INSTL-001-2026", "report_no": "001/INSTL /TAP/01-2026"}])
    )
    app.dependency_overrides[get_installation_gateway] = lambda: fake

    response = client.get("/api/ltsa/installations")

    assert response.status_code == 200
    assert response.json() == fake.list_response
    assert fake.list_calls == 1


def test_get_installation_returns_the_gateways_response_unchanged():
    fake = FakeInstallationGateway(detail_response=_response({"installation_code": "INSTL-001-2026"}))
    app.dependency_overrides[get_installation_gateway] = lambda: fake

    response = client.get("/api/ltsa/installations/INSTL-001-2026")

    assert response.status_code == 200
    assert response.json() == fake.detail_response
    assert fake.detail_calls == ["INSTL-001-2026"]


def test_list_installations_propagates_a_failure_response_unchanged():
    fake = FakeInstallationGateway(list_response={"success": False, "message": "n8n unreachable"})
    app.dependency_overrides[get_installation_gateway] = lambda: fake

    response = client.get("/api/ltsa/installations")

    assert response.status_code == 200
    assert response.json()["success"] is False


# --- MWO-LTSA-SEAL-INSTALLATION-FITMENT-001 -- structured linkage routes ---
#
# Distinct from FakeInstallationGateway above (n8n-backed raw-document
# routes, unchanged): these new routes go through a NEW repository +
# link_installation_report() (imported directly into the router, same
# apply_lifecycle_event/create_warranty_assessment precedent -- only its
# `runner` parameter is a FastAPI dependency), so a FakeRunner returning
# one canned response per sequential query_scalar() call is reused here.


_VALID_SEAL_UNIT_ID = "11111111-1111-4111-8111-111111111111"
_VALID_INSTALL_EVENT_ID = "77777777-7777-4777-8777-777777777777"
_INSTALLATION_CODE = "INST-001"


class FakeInstallationReportFitmentRepository:
    def __init__(self, *, reports=None):
        self.reports = reports if reports is not None else []

    def find_by_code(self, installation_code):
        for r in self.reports:
            if r["installation_code"] == installation_code:
                return r
        return None

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


class SequencedFakeRunner:
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.query_scalar_calls: list[str] = []

    def query_scalar(self, sql):
        self.query_scalar_calls.append(sql)
        return self.responses.pop(0) if self.responses else "[]"


def _report_row(**overrides):
    row = {
        "installation_code": _INSTALLATION_CODE, "seal_unit_id": None, "pump_tag_number": None,
        "seal_code": None, "installation_event_id": None,
    }
    row.update(overrides)
    return json.dumps([row])


def _unit_row():
    return json.dumps([{"seal_unit_id": _VALID_SEAL_UNIT_ID, "seal_code": "JC-TYPE-X"}])


def _event_row(**overrides):
    row = {
        "event_id": _VALID_INSTALL_EVENT_ID, "seal_unit_id": _VALID_SEAL_UNIT_ID, "event_type": "INSTALL",
        "pump_tag_number": "110-P-9A",
    }
    row.update(overrides)
    return json.dumps([row])


def _linked_row(**overrides):
    row = {
        "installation_code": _INSTALLATION_CODE, "report_no": "RPT-001", "report_date": None,
        "plant_equip_no": None, "seal_code": None, "seal_unit_id": _VALID_SEAL_UNIT_ID,
        "pump_tag_number": "110-P-9A", "installation_event_id": _VALID_INSTALL_EVENT_ID,
        "linked_by": "server-actor", "link_reason": "x",
        "source_document_name": "doc.pdf", "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-06T00:00:00",
    }
    row.update(overrides)
    return json.dumps([row])


def _happy_link_responses():
    return [_report_row(), _unit_row(), _event_row(), _linked_row()]


@pytest.fixture(autouse=True)
def clear_dependency_overrides_fitment():
    yield
    app.dependency_overrides.clear()


def test_new_fitment_routes_are_registered_with_no_patch_or_delete():
    openapi = client.get("/openapi.json").json()["paths"]
    assert set(openapi["/api/ltsa/seal-units/{seal_unit_id}/installation-reports"]) == {"get"}
    assert set(openapi["/api/ltsa/installation-reports/by-pump/{pump_tag_number}"]) == {"get"}
    assert set(openapi["/api/ltsa/installation-reports/{installation_code}"]) == {"get"}
    assert set(openapi["/api/ltsa/installation-reports/{installation_code}/link-installation"]) == {"post"}
    for path in openapi:
        if "installation-reports" in path:
            assert "patch" not in openapi[path] and "delete" not in openapi[path]


def test_get_report_detail_404s_for_an_unknown_code():
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_installation_report_fitment_repository] = lambda: FakeInstallationReportFitmentRepository()
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({})
    response = client.get(f"/api/ltsa/installation-reports/{_INSTALLATION_CODE}")
    assert response.status_code == 404


# --- write permission matrix -----------------------------------------------

def test_link_succeeds_for_superuser_and_tap_admin_only():
    for role in ("SUPERUSER", "TAP_ADMIN"):
        fake_runner = SequencedFakeRunner(_happy_link_responses())
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post(
            f"/api/ltsa/installation-reports/{_INSTALLATION_CODE}/link-installation",
            json={
                "seal_unit_id": _VALID_SEAL_UNIT_ID, "installation_event_id": _VALID_INSTALL_EVENT_ID,
                "pump_tag_number": "110-P-9A", "reason": "linking legacy report",
            },
        )
        assert response.status_code == 200, f"{role} should be authorized"


def test_link_denied_for_read_only_roles():
    for role in ("TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
        fake_runner = SequencedFakeRunner(_happy_link_responses())
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post(
            f"/api/ltsa/installation-reports/{_INSTALLATION_CODE}/link-installation",
            json={
                "seal_unit_id": _VALID_SEAL_UNIT_ID, "installation_event_id": _VALID_INSTALL_EVENT_ID,
                "pump_tag_number": "110-P-9A", "reason": "x",
            },
        )
        assert response.status_code == 403, f"{role} must be denied"
        assert fake_runner.query_scalar_calls == []


# --- actor spoof prevented --------------------------------------------------

def test_link_actor_is_always_the_authenticated_user():
    fake_runner = SequencedFakeRunner(_happy_link_responses())
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN", user_id="real-actor")
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/installation-reports/{_INSTALLATION_CODE}/link-installation",
        json={
            "seal_unit_id": _VALID_SEAL_UNIT_ID, "installation_event_id": _VALID_INSTALL_EVENT_ID,
            "pump_tag_number": "110-P-9A", "reason": "x", "linked_by": "spoofed",
        },
    )
    assert response.status_code == 200
    # linked_by isn't a real InstallationReportLinkRequest field -- silently
    # dropped by pydantic; the actual value written into the guarded UPDATE
    # is always current_user.user_id.
    update_sql = fake_runner.query_scalar_calls[-1]
    assert "real-actor" in update_sql
    assert "spoofed" not in update_sql


# --- error mapping -----------------------------------------------------

def test_link_maps_unknown_report_to_404():
    fake_runner = SequencedFakeRunner([json.dumps([])])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/installation-reports/{_INSTALLATION_CODE}/link-installation",
        json={
            "seal_unit_id": _VALID_SEAL_UNIT_ID, "installation_event_id": _VALID_INSTALL_EVENT_ID,
            "pump_tag_number": "110-P-9A", "reason": "x",
        },
    )
    assert response.status_code == 404


def test_link_maps_already_linked_to_409():
    fake_runner = SequencedFakeRunner([_report_row(installation_event_id="99999999-9999-4999-8999-999999999999")])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/installation-reports/{_INSTALLATION_CODE}/link-installation",
        json={
            "seal_unit_id": _VALID_SEAL_UNIT_ID, "installation_event_id": _VALID_INSTALL_EVENT_ID,
            "pump_tag_number": "110-P-9A", "reason": "x",
        },
    )
    assert response.status_code == 409


def test_link_maps_non_install_event_to_422():
    fake_runner = SequencedFakeRunner([_report_row(), _unit_row(), _event_row(event_type="REGISTERED")])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/installation-reports/{_INSTALLATION_CODE}/link-installation",
        json={
            "seal_unit_id": _VALID_SEAL_UNIT_ID, "installation_event_id": _VALID_INSTALL_EVENT_ID,
            "pump_tag_number": "110-P-9A", "reason": "x",
        },
    )
    assert response.status_code == 422


def test_link_requires_a_reason_before_touching_the_runner():
    fake_runner = SequencedFakeRunner(_happy_link_responses())
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/installation-reports/{_INSTALLATION_CODE}/link-installation",
        json={
            "seal_unit_id": _VALID_SEAL_UNIT_ID, "installation_event_id": _VALID_INSTALL_EVENT_ID,
            "pump_tag_number": "110-P-9A", "reason": "",
        },
    )
    assert response.status_code == 422
    assert fake_runner.query_scalar_calls == []


# --- malformed UUID clean ---------------------------------------------

def test_link_malformed_seal_unit_id_is_a_clean_404():
    fake_runner = SequencedFakeRunner([_report_row()])
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        f"/api/ltsa/installation-reports/{_INSTALLATION_CODE}/link-installation",
        json={"seal_unit_id": "not-a-uuid", "installation_event_id": _VALID_INSTALL_EVENT_ID, "pump_tag_number": "110-P-9A", "reason": "x"},
    )
    assert response.status_code == 404


# --- area scope: pump-linked report scoped, legacy fails closed -----------

def test_area_scoped_identity_sees_only_reports_whose_structured_pump_is_in_scope():
    reports = [
        {"installation_code": "IN-SCOPE", "seal_unit_id": _VALID_SEAL_UNIT_ID, "pump_tag_number": "110-P-9A"},
        {"installation_code": "OUT-OF-SCOPE", "seal_unit_id": _VALID_SEAL_UNIT_ID, "pump_tag_number": "211-P-1A"},
        {"installation_code": "LEGACY", "seal_unit_id": _VALID_SEAL_UNIT_ID, "pump_tag_number": None},
    ]
    app.dependency_overrides[get_installation_report_fitment_repository] = (
        lambda: FakeInstallationReportFitmentRepository(reports=reports)
    )
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({"110-P-9A": "HOC", "211-P-1A": "HCC"})
    app.dependency_overrides[get_current_user] = (
        lambda: _identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC")
    )
    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/installation-reports")
    assert response.status_code == 200
    # 19: cross-scope read denied (OUT-OF-SCOPE excluded).
    # Legacy/unstructured report fails closed for a scoped identity too.
    assert {r["installation_code"] for r in response.json()["data"]} == {"IN-SCOPE"}


def test_unrestricted_role_sees_every_report_regardless_of_pump():
    reports = [
        {"installation_code": "A", "seal_unit_id": _VALID_SEAL_UNIT_ID, "pump_tag_number": "110-P-9A"},
        {"installation_code": "B", "seal_unit_id": _VALID_SEAL_UNIT_ID, "pump_tag_number": None},
    ]
    app.dependency_overrides[get_installation_report_fitment_repository] = (
        lambda: FakeInstallationReportFitmentRepository(reports=reports)
    )
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({"110-P-9A": "HOC"})
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/installation-reports")
    assert response.status_code == 200
    assert {r["installation_code"] for r in response.json()["data"]} == {"A", "B"}
