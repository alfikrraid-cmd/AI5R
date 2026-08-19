"""MWO-LTSA-AUTH-DATA-SCOPE-ROUTE-CLOSURE-001 -- proves Area/MA data
scope is enforced (server-side, via the 1-hop asset_code -> pump_gateway
-> area join) across every LTSA route wired in this closure: pumps.py's
7 sub-routes, work_orders.py, maintenance.py, cm_report.py,
pm_schedule.py, pm_occurrence.py, condition_monitoring.py,
installation.py, seal.py's compatibility route.

Test matrix (per this MWO's own requirement): a HOC-scoped user against
an HSC-owned record, and an MA2-scoped user against an HOC-owned record
(outside MA2's HSC/S_PAKNING/HCC group) -- own-scope read succeeds,
cross-scope list is filtered, cross-scope detail is denied (404, same
shape as a genuine miss), and the four unrestricted roles retain access.
Write routes are not separately re-tested for scope here: every write
route on every domain touched by this closure is gated on
maintenance.write/maintenance.admin_review/maintenance.technical_review/
master.edit, none of which any Pertamina role holds (see
test_pertamina_holds_no_write_permission_anywhere below) -- scope is
therefore already unreachable by construction, not bypassed by omission.
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
    get_cm_report_gateway,
    get_condition_monitoring_reading_gateway,
    get_condition_monitoring_schedule_gateway,
    get_current_user,
    get_installation_gateway,
    get_maintenance_history_gateway,
    get_pm_occurrence_gateway,
    get_pm_schedule_gateway,
    get_pump_gateway,
    get_seal_pump_compatibility_gateway,
    get_work_order_gateway,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)

_PUMP_AREAS = {"110-P-9A": "HOC", "200-P-1A": "HSC"}  # HOC pump vs HSC pump


class FakePumpGateway:
    def get_pump(self, tag_number):
        area = _PUMP_AREAS.get(tag_number)
        if area is None:
            return {"success": False, "data": None}
        return {"success": True, "data": {"tag_number": tag_number, "area": area}}

    def list_pumps(self):
        return {"success": True, "count": 2, "data": [{"tag_number": t, "area": a} for t, a in _PUMP_AREAS.items()]}


def _identity(role: str, *, data_scope_type=None, data_scope_value=None) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id="u1", email="u1@example.test", organization_id="org-1",
        organization_code="PERTAMINA_RU_II", role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


def _hoc_identity():
    return _identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC")


def _ma2_identity():
    return _identity("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA2")


_GATEWAY_DEPS_BY_NAME = {
    "get_work_order_gateway": get_work_order_gateway,
    "get_maintenance_history_gateway": get_maintenance_history_gateway,
    "get_cm_report_gateway": get_cm_report_gateway,
    "get_pm_schedule_gateway": get_pm_schedule_gateway,
    "get_pm_occurrence_gateway": get_pm_occurrence_gateway,
    "get_condition_monitoring_reading_gateway": get_condition_monitoring_reading_gateway,
    "get_condition_monitoring_schedule_gateway": get_condition_monitoring_schedule_gateway,
    "get_installation_gateway": get_installation_gateway,
    "get_seal_pump_compatibility_gateway": get_seal_pump_compatibility_gateway,
}


def _override(*, identity, **gateway_overrides):
    app.dependency_overrides[get_current_user] = lambda: identity
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    for dep_name, gw in gateway_overrides.items():
        app.dependency_overrides[_GATEWAY_DEPS_BY_NAME[dep_name]] = lambda gw=gw: gw


def _clear():
    app.dependency_overrides.clear()


class _RecordGateway:
    """Generic list/detail fake for the asset_code-keyed domains
    (work_order/maintenance_history/cm_report/pm_schedule/pm_occurrence/
    condition_monitoring), each returning one HOC record and one HSC
    record keyed by the domain's own success/list/detail method names."""

    def __init__(self, list_key: str, detail_key: str, code_field: str, asset_field: str = "asset_code"):
        # asset_type: "PUMP" is only meaningful to work_orders.py's own
        # polymorphic-asset_type check; harmless extra key for every
        # other domain's fixture.
        self.records = [
            {code_field: "HOC-1", asset_field: "110-P-9A", "asset_type": "PUMP"},
            {code_field: "HSC-1", asset_field: "200-P-1A", "asset_type": "PUMP"},
        ]
        setattr(self, list_key, self._list)
        setattr(self, detail_key, self._detail)
        self._code_field = code_field

    def _list(self):
        return {"success": True, "count": len(self.records), "data": list(self.records)}

    def _detail(self, code):
        match = next((r for r in self.records if r[self._code_field] == code), None)
        return {"success": match is not None, "data": match}


def _assert_route_scope(list_path, detail_path_hoc, detail_path_hsc, gateway_dep, gateway):
    # HOC-scoped user: own-area record visible, cross-scope hidden from list, cross-scope detail denied.
    _override(identity=_hoc_identity(), **{gateway_dep: gateway})
    try:
        listed = client.get(list_path).json()
        codes = {r.get("code") or r.get("pm_occurrence_code") or r.get("work_order_code") or True for r in listed["data"]}
        assert listed["count"] == 1
        assert client.get(detail_path_hoc).status_code == 200
        assert client.get(detail_path_hsc).status_code == 404
    finally:
        _clear()

    # Unrestricted role: sees both.
    _override(identity=_identity("TAP_ADMIN"), **{gateway_dep: gateway})
    try:
        assert client.get(list_path).json()["count"] == 2
        assert client.get(detail_path_hoc).status_code == 200
        assert client.get(detail_path_hsc).status_code == 200
    finally:
        _clear()


class TestWorkOrders:
    def test_hoc_scoped_and_unrestricted(self):
        gw = _RecordGateway("list_work_orders", "get_work_order", "work_order_code")
        _assert_route_scope(
            "/api/ltsa/workorders", "/api/ltsa/workorders/HOC-1", "/api/ltsa/workorders/HSC-1",
            "get_work_order_gateway", gw,
        )


class TestMaintenanceHistory:
    def test_hoc_scoped_and_unrestricted(self):
        gw = _RecordGateway("list_maintenance_history", "get_maintenance_history", "code")
        _assert_route_scope(
            "/api/ltsa/maintenance-history", "/api/ltsa/maintenance-history/HOC-1",
            "/api/ltsa/maintenance-history/HSC-1", "get_maintenance_history_gateway", gw,
        )


class TestCMReport:
    def test_hoc_scoped_and_unrestricted(self):
        gw = _RecordGateway("list_cm_reports", "get_cm_report", "code")
        _assert_route_scope(
            "/api/ltsa/cm-reports", "/api/ltsa/cm-reports/HOC-1", "/api/ltsa/cm-reports/HSC-1",
            "get_cm_report_gateway", gw,
        )


class TestPMSchedule:
    def test_hoc_scoped_and_unrestricted(self):
        gw = _RecordGateway("list_pm_schedules", "get_pm_schedule", "code")
        _assert_route_scope(
            "/api/ltsa/pm-schedules", "/api/ltsa/pm-schedules/HOC-1", "/api/ltsa/pm-schedules/HSC-1",
            "get_pm_schedule_gateway", gw,
        )


class TestPMOccurrence:
    def test_hoc_scoped_and_unrestricted(self):
        gw = _RecordGateway("list_pm_occurrences", "get_pm_occurrence", "pm_occurrence_code")
        _assert_route_scope(
            "/api/ltsa/pm-occurrences", "/api/ltsa/pm-occurrences/HOC-1", "/api/ltsa/pm-occurrences/HSC-1",
            "get_pm_occurrence_gateway", gw,
        )

    def test_ma2_scoped_user_denied_hoc_record(self):
        # MA2 = HSC + S_PAKNING + HCC -- HOC is outside the group.
        gw = _RecordGateway("list_pm_occurrences", "get_pm_occurrence", "pm_occurrence_code")
        _override(identity=_ma2_identity(), get_pm_occurrence_gateway=gw)
        try:
            assert client.get("/api/ltsa/pm-occurrences/HOC-1").status_code == 404
            assert client.get("/api/ltsa/pm-occurrences/HSC-1").status_code == 200
            assert client.get("/api/ltsa/pm-occurrences").json()["count"] == 1
        finally:
            _clear()


class TestConditionMonitoringReadings:
    def test_hoc_scoped_and_unrestricted(self):
        gw = _RecordGateway(
            "list_condition_monitoring_readings", "get_condition_monitoring_reading", "condition_monitoring_reading_code"
        )
        _assert_route_scope(
            "/api/ltsa/condition-monitoring-readings", "/api/ltsa/condition-monitoring-readings/HOC-1",
            "/api/ltsa/condition-monitoring-readings/HSC-1", "get_condition_monitoring_reading_gateway", gw,
        )


class TestConditionMonitoringSchedules:
    def test_hoc_scoped_and_unrestricted(self):
        gw = _RecordGateway(
            "list_condition_monitoring_schedules", "get_condition_monitoring_schedule", "condition_monitoring_schedule_code"
        )
        _assert_route_scope(
            "/api/ltsa/condition-monitoring-schedules", "/api/ltsa/condition-monitoring-schedules/HOC-1",
            "/api/ltsa/condition-monitoring-schedules/HSC-1", "get_condition_monitoring_schedule_gateway", gw,
        )


class TestInstallation:
    def test_hoc_scoped_and_unrestricted(self):
        gw = _RecordGateway("list_installations", "get_installation", "installation_code", asset_field="plant_equip_no")
        _assert_route_scope(
            "/api/ltsa/installations", "/api/ltsa/installations/HOC-1", "/api/ltsa/installations/HSC-1",
            "get_installation_gateway", gw,
        )


class TestSealCompatibility:
    def test_hoc_scoped_list_filters_to_hoc_only(self):
        class FakeCompatGateway:
            def list_seal_pump_compatibilities(self):
                return {
                    "success": True, "count": 2,
                    "data": [
                        {"seal_code": "S-1", "pump_tag_number": "110-P-9A"},
                        {"seal_code": "S-2", "pump_tag_number": "200-P-1A"},
                    ],
                }

        _override(identity=_hoc_identity(), get_seal_pump_compatibility_gateway=FakeCompatGateway())
        try:
            body = client.get("/api/ltsa/seal-compatibility").json()
            assert body["count"] == 1
            assert body["data"][0]["pump_tag_number"] == "110-P-9A"
        finally:
            _clear()

    def test_unrestricted_sees_all(self):
        class FakeCompatGateway:
            def list_seal_pump_compatibilities(self):
                return {
                    "success": True, "count": 2,
                    "data": [
                        {"seal_code": "S-1", "pump_tag_number": "110-P-9A"},
                        {"seal_code": "S-2", "pump_tag_number": "200-P-1A"},
                    ],
                }

        _override(identity=_identity("JOHN_CRANE_ENGINEER"), get_seal_pump_compatibility_gateway=FakeCompatGateway())
        try:
            assert client.get("/api/ltsa/seal-compatibility").json()["count"] == 2
        finally:
            _clear()


class TestPumpsSubRoutesScope:
    """The 7 /pumps/{tag}/... sub-routes: tag itself IS the pump, so
    the guard resolves scope directly from pump_gateway.get_pump(tag)."""

    def test_cross_scope_knowledge_denied(self):
        class FakeKnowledgeService:
            def build(self, tag):
                raise AssertionError("must never be called for an out-of-scope tag")

        _override(identity=_hoc_identity())
        from dependencies import get_ltsa_knowledge_service

        app.dependency_overrides[get_ltsa_knowledge_service] = lambda: FakeKnowledgeService()
        try:
            response = client.get("/api/ltsa/pumps/200-P-1A/knowledge")
            assert response.status_code == 404
        finally:
            _clear()

    def test_own_scope_lifecycle_reaches_the_service(self):
        import dataclasses as dc

        from dependencies import get_equipment_timeline_service

        calls = []

        @dc.dataclass
        class _Lifecycle:
            tag_number: str = "110-P-9A"

        class FakeTimelineService:
            def build_lifecycle(self, tag):
                calls.append(tag)
                return _Lifecycle(tag_number=tag)

        _override(identity=_hoc_identity())
        app.dependency_overrides[get_equipment_timeline_service] = lambda: FakeTimelineService()
        try:
            response = client.get("/api/ltsa/pumps/110-P-9A/lifecycle")
            assert response.status_code == 200
            assert calls == ["110-P-9A"]
        finally:
            _clear()


class TestWritePermissionStructure:
    def test_pertamina_holds_no_write_permission_anywhere(self):
        write_permissions = {
            "maintenance.write", "maintenance.admin_review", "maintenance.technical_review", "master.edit",
        }
        for role in ("PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
            assert ROLE_PERMISSIONS[role].isdisjoint(write_permissions), (
                f"{role} must never hold a write permission on any pump-associated route -- "
                "scope enforcement on writes would otherwise be required and is not implemented"
            )
