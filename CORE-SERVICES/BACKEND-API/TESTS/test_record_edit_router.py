"""MWO-LTSA-AUDIT-CHANGE-HISTORY-001 -- router-level proof: backend-
enforced record.edit/audit.read_full permission gates, actor derivation,
cross-scope denial (reusing 187578d's own scope architecture), and the
no-op/reason/allowlist rejections surfacing as the right HTTP status.
"""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from main import app  # noqa: E402
from dependencies import (  # noqa: E402
    get_current_user,
    get_import_database_runner,
    get_pump_gateway,
    get_record_change_history_repository,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)


def _identity(role: str, *, data_scope_type=None, data_scope_value=None) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id="actor-1", email="actor@example.test", organization_id="org-1",
        organization_code="TAP", role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


class FakeRunner:
    def __init__(self, row):
        self.row = row
        self.query_scalar_calls = []
        self.execute_script_calls = []

    def query_scalar(self, sql):
        import json
        self.query_scalar_calls.append(sql)
        return json.dumps([self.row])

    def execute_script(self, sql):
        self.execute_script_calls.append(sql)


class FakePumpGateway:
    def get_pump(self, tag_number):
        return {"success": True, "data": {"tag_number": tag_number, "area": "HOC"}}


class FakeHistoryRepository:
    def __init__(self, rows):
        self.rows = rows

    def list_for_entity(self, entity_type, entity_id):
        return self.rows


def _clear():
    app.dependency_overrides.clear()


_CMON_ROW = {
    "condition_monitoring_reading_code": "CMONR-1",
    "mechseal_temp_de": 58.0,
    "asset_code": "110-P-9A",
}

_EDIT_BODY = {
    "entity_type": "CONDITION_MONITORING_READING",
    "entity_id": "CMONR-1",
    "field_name": "mechseal_temp_de",
    "new_value": 61.5,
    "reason": "Re-read per JC field report 2026-08-15",
}


class TestEditPermission:
    def test_superuser_can_edit(self):
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        app.dependency_overrides[get_import_database_runner] = lambda: FakeRunner(_CMON_ROW)
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        try:
            response = client.post("/api/ltsa/records/edit", json=_EDIT_BODY)
            assert response.status_code == 200
            assert response.json()["data"]["no_op"] is False
        finally:
            _clear()

    def test_tap_admin_can_edit(self):
        app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
        app.dependency_overrides[get_import_database_runner] = lambda: FakeRunner(_CMON_ROW)
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        try:
            response = client.post("/api/ltsa/records/edit", json=_EDIT_BODY)
            assert response.status_code == 200
        finally:
            _clear()

    def test_tap_engineer_denied(self):
        app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")
        app.dependency_overrides[get_import_database_runner] = lambda: FakeRunner(_CMON_ROW)
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        try:
            assert client.post("/api/ltsa/records/edit", json=_EDIT_BODY).status_code == 403
        finally:
            _clear()

    def test_john_crane_engineer_denied(self):
        app.dependency_overrides[get_current_user] = lambda: _identity("JOHN_CRANE_ENGINEER")
        app.dependency_overrides[get_import_database_runner] = lambda: FakeRunner(_CMON_ROW)
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        try:
            assert client.post("/api/ltsa/records/edit", json=_EDIT_BODY).status_code == 403
        finally:
            _clear()

    def test_pertamina_engineer_denied(self):
        app.dependency_overrides[get_current_user] = lambda: _identity(
            "PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"
        )
        app.dependency_overrides[get_import_database_runner] = lambda: FakeRunner(_CMON_ROW)
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        try:
            assert client.post("/api/ltsa/records/edit", json=_EDIT_BODY).status_code == 403
        finally:
            _clear()

    def test_actor_id_in_written_script_is_the_authenticated_user_never_request_supplied(self):
        # RecordEditRequest has no actor/changed_by field at all -- proven
        # here by supplying one anyway and confirming it's ignored
        # (Pydantic drops unknown fields by default; the written script
        # only ever contains the real authenticated actor's id).
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        runner = FakeRunner(_CMON_ROW)
        app.dependency_overrides[get_import_database_runner] = lambda: runner
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        try:
            body = {**_EDIT_BODY, "changed_by": "spoofed-user", "actor_id": "spoofed-user"}
            client.post("/api/ltsa/records/edit", json=body)
            script = runner.execute_script_calls[0]
            assert "'actor-1'" in script
            assert "spoofed-user" not in script
        finally:
            _clear()

    def test_reason_required_returns_422(self):
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        app.dependency_overrides[get_import_database_runner] = lambda: FakeRunner(_CMON_ROW)
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        try:
            response = client.post("/api/ltsa/records/edit", json={**_EDIT_BODY, "reason": ""})
            assert response.status_code == 422
        finally:
            _clear()

    def test_non_allowlisted_field_returns_422(self):
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        app.dependency_overrides[get_import_database_runner] = lambda: FakeRunner(_CMON_ROW)
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        try:
            response = client.post(
                "/api/ltsa/records/edit", json={**_EDIT_BODY, "field_name": "workflow_status"}
            )
            assert response.status_code == 422
        finally:
            _clear()

    def test_editor_roles_are_always_unrestricted_by_scope_never_weakened(self):
        # record.edit is granted ONLY to SUPERUSER/TAP_ADMIN, and both are
        # members of auth_service._UNRESTRICTED_ROLES -- so cross-scope
        # denial can never trigger for an editor today by construction.
        # This is the honest "Edit must also respect existing scope
        # architecture -- do not weaken it" proof for this specific
        # capability: scope is still evaluated (see record_edit_service.
        # edit_value's own scope branch and its dedicated unit tests in
        # test_record_edit_service.py), it simply never restricts these
        # two roles, exactly like the data-scope MWOs' own write-route
        # closures already established for every other write.
        from API.auth_service import resolve_area_scope

        assert resolve_area_scope(_identity("SUPERUSER")) is None
        assert resolve_area_scope(_identity("TAP_ADMIN")) is None

    def test_cross_scope_edit_denied_as_404_if_a_restricted_identity_ever_gained_record_edit(self):
        # Defense-in-depth proof: even though no role today combines
        # record.edit with a scope restriction, the router still passes
        # resolve_area_scope(current_user) into edit_value() unconditionally
        # (never special-cased per role) -- so if a future role ever
        # combines both, the same 404 (not 403) cross-scope denial this
        # session's other closures established would apply automatically.
        # Proven directly against the service (bypassing the permission
        # gate, which is a separate, already-tested concern) rather than
        # inventing a fake role in ROLE_PERMISSIONS.
        from API.record_edit_service import RecordNotFoundError, edit_value

        runner = FakeRunner(_CMON_ROW)  # asset_code 110-P-9A, area HOC (FakePumpGateway below)

        class HSCPumpGateway:
            def get_pump(self, tag_number):
                return {"success": True, "data": {"tag_number": tag_number, "area": "HSC"}}

        try:
            edit_value(
                entity_type="CONDITION_MONITORING_READING", entity_id="CMONR-1",
                field_name="mechseal_temp_de", new_value=61.5, reason="fix",
                actor_id="actor-1", scope=frozenset({"HOC"}), runner=runner,
                pump_gateway=HSCPumpGateway(),
            )
            raise AssertionError("expected RecordNotFoundError")
        except RecordNotFoundError:
            pass
        assert runner.execute_script_calls == []

    def test_no_op_edit_reported_and_writes_nothing(self):
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        runner = FakeRunner(_CMON_ROW)
        app.dependency_overrides[get_import_database_runner] = lambda: runner
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        try:
            response = client.post("/api/ltsa/records/edit", json={**_EDIT_BODY, "new_value": 58.0})
            assert response.json()["data"]["no_op"] is True
            assert runner.execute_script_calls == []
        finally:
            _clear()


class TestHistoryPermission:
    def test_superuser_can_read_history(self):
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        app.dependency_overrides[get_record_change_history_repository] = lambda: FakeHistoryRepository(
            [{"change_id": "1", "field_name": "mechseal_temp_de", "old_value": "58.0", "new_value": "61.5"}]
        )
        try:
            response = client.get(
                "/api/ltsa/records/history",
                params={"entity_type": "CONDITION_MONITORING_READING", "entity_id": "CMONR-1"},
            )
            assert response.status_code == 200
            assert len(response.json()["data"]) == 1
        finally:
            _clear()

    def test_tap_admin_history_read_is_403(self):
        app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
        app.dependency_overrides[get_record_change_history_repository] = lambda: FakeHistoryRepository([])
        try:
            response = client.get(
                "/api/ltsa/records/history",
                params={"entity_type": "CONDITION_MONITORING_READING", "entity_id": "CMONR-1"},
            )
            assert response.status_code == 403
        finally:
            _clear()

    def test_other_roles_history_read_is_403(self):
        for role in ("TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
            app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
            app.dependency_overrides[get_record_change_history_repository] = lambda: FakeHistoryRepository([])
            try:
                response = client.get(
                    "/api/ltsa/records/history",
                    params={"entity_type": "CONDITION_MONITORING_READING", "entity_id": "CMONR-1"},
                )
                assert response.status_code == 403, f"{role} must be denied"
            finally:
                _clear()


class TestNoUpdateDeleteEndpointExists:
    def test_no_delete_route_for_history_registered(self):
        response = client.delete(
            "/api/ltsa/records/history",
            params={"entity_type": "CONDITION_MONITORING_READING", "entity_id": "CMONR-1"},
        )
        assert response.status_code in (404, 405)

    def test_repository_exposes_no_update_or_delete_method(self):
        from API.record_change_history_repository import RecordChangeHistoryRepository

        assert not hasattr(RecordChangeHistoryRepository, "update")
        assert not hasattr(RecordChangeHistoryRepository, "delete")
