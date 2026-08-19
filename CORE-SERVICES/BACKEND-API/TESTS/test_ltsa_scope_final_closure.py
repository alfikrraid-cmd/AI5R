"""MWO-LTSA-AUTH-DATA-SCOPE-FINAL-CLOSURE-001 -- proves the two remaining
blockers from fe8695d are closed: pm_cm_evidence.py/document.py's 2-hop
pump joins, and fleet.py/copilot.py's fleet-wide aggregate leak (filtered
at the data layer BEFORE aggregation, never merely hiding pump names
after computing a global result).
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
    get_condition_monitoring_reading_gateway,
    get_current_user,
    get_fleet_executive_summary_service,
    get_fleet_reliability_service,
    get_pm_cm_evidence_repository,
    get_pm_occurrence_gateway,
    get_pump_gateway,
    get_seal_engineering_document_gateway,
    get_seal_pump_compatibility_gateway,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402
from API.fleet_reliability_service import FleetReliability  # noqa: E402
from API.fleet_executive_summary import FleetExecutiveSummary, TopRisk  # noqa: E402

client = TestClient(app)

_PUMP_AREAS = {"110-P-9A": "HOC", "200-P-1A": "HSC", "300-P-1A": "HCC"}


class FakePumpGateway:
    def get_pump(self, tag_number):
        area = _PUMP_AREAS.get(tag_number)
        if area is None:
            return {"success": False, "data": None}
        return {"success": True, "data": {"tag_number": tag_number, "area": area}}

    def list_pumps(self):
        return {"success": True, "data": [{"tag_number": t, "area": a} for t, a in _PUMP_AREAS.items()]}


def _identity(role: str, *, data_scope_type=None, data_scope_value=None) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id="u1", email="u1@example.test", organization_id="org-1",
        organization_code="PERTAMINA_RU_II", role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


def _hoc():
    return _identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC")


def _ma2():
    return _identity("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA2")


def _clear():
    app.dependency_overrides.clear()


# --- pm_cm_evidence.py ------------------------------------------------


class FakePMOccurrenceGateway:
    def get_pm_occurrence(self, code):
        by_code = {"PMOCC-HOC": "110-P-9A", "PMOCC-HSC": "200-P-1A"}
        asset = by_code.get(code)
        return {"success": asset is not None, "data": {"asset_code": asset} if asset else None}


class FakeCMONGateway:
    def get_condition_monitoring_reading(self, code):
        return {"success": False, "data": None}


class FakeEvidenceRepository:
    def list_for_record(self, record_type, record_code):
        return [{"evidence_id": "EV-1", "record_type": record_type, "record_code": record_code}]

    def get_file_data(self, evidence_id):
        by_id = {
            "EV-HOC": {"record_type": "PM_OCCURRENCE", "record_code": "PMOCC-HOC", "content_type": "image/png",
                       "file_data_base64": "aGVsbG8="},
            "EV-HSC": {"record_type": "PM_OCCURRENCE", "record_code": "PMOCC-HSC", "content_type": "image/png",
                       "file_data_base64": "aGVsbG8="},
        }
        return by_id.get(evidence_id)


class TestPMCMEvidenceScope:
    def test_hoc_cannot_list_hsc_evidence(self):
        app.dependency_overrides[get_current_user] = lambda: _hoc()
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        app.dependency_overrides[get_pm_occurrence_gateway] = lambda: FakePMOccurrenceGateway()
        app.dependency_overrides[get_condition_monitoring_reading_gateway] = lambda: FakeCMONGateway()
        app.dependency_overrides[get_pm_cm_evidence_repository] = lambda: FakeEvidenceRepository()
        try:
            response = client.get(
                "/api/ltsa/pm-cm-evidence", params={"record_type": "PM_OCCURRENCE", "record_code": "PMOCC-HSC"}
            )
            assert response.json()["data"] == []
        finally:
            _clear()

    def test_hoc_can_list_own_evidence(self):
        app.dependency_overrides[get_current_user] = lambda: _hoc()
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        app.dependency_overrides[get_pm_occurrence_gateway] = lambda: FakePMOccurrenceGateway()
        app.dependency_overrides[get_condition_monitoring_reading_gateway] = lambda: FakeCMONGateway()
        app.dependency_overrides[get_pm_cm_evidence_repository] = lambda: FakeEvidenceRepository()
        try:
            response = client.get(
                "/api/ltsa/pm-cm-evidence", params={"record_type": "PM_OCCURRENCE", "record_code": "PMOCC-HOC"}
            )
            assert len(response.json()["data"]) == 1
        finally:
            _clear()

    def test_hoc_cannot_download_hsc_evidence_and_leaks_no_existence(self):
        app.dependency_overrides[get_current_user] = lambda: _hoc()
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        app.dependency_overrides[get_pm_occurrence_gateway] = lambda: FakePMOccurrenceGateway()
        app.dependency_overrides[get_condition_monitoring_reading_gateway] = lambda: FakeCMONGateway()
        app.dependency_overrides[get_pm_cm_evidence_repository] = lambda: FakeEvidenceRepository()
        try:
            cross_scope = client.get("/api/ltsa/pm-cm-evidence/EV-HSC/download")
            genuinely_missing = client.get("/api/ltsa/pm-cm-evidence/NOT-REAL/download")
            assert cross_scope.status_code == genuinely_missing.status_code == 404
            assert cross_scope.json() == genuinely_missing.json()
        finally:
            _clear()

    def test_hoc_can_download_own_evidence(self):
        app.dependency_overrides[get_current_user] = lambda: _hoc()
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        app.dependency_overrides[get_pm_occurrence_gateway] = lambda: FakePMOccurrenceGateway()
        app.dependency_overrides[get_condition_monitoring_reading_gateway] = lambda: FakeCMONGateway()
        app.dependency_overrides[get_pm_cm_evidence_repository] = lambda: FakeEvidenceRepository()
        try:
            assert client.get("/api/ltsa/pm-cm-evidence/EV-HOC/download").status_code == 200
        finally:
            _clear()

    def test_unrestricted_role_sees_hsc_evidence(self):
        app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        app.dependency_overrides[get_pm_occurrence_gateway] = lambda: FakePMOccurrenceGateway()
        app.dependency_overrides[get_condition_monitoring_reading_gateway] = lambda: FakeCMONGateway()
        app.dependency_overrides[get_pm_cm_evidence_repository] = lambda: FakeEvidenceRepository()
        try:
            assert client.get("/api/ltsa/pm-cm-evidence/EV-HSC/download").status_code == 200
        finally:
            _clear()


# --- document.py --------------------------------------------------------


class FakeDocumentGateway:
    def list_seal_engineering_documents(self):
        return {"success": True, "count": 2, "data": [{"seal_code": "S-HOC"}, {"seal_code": "S-HSC"}]}


class FakeCompatGateway:
    def list_seal_pump_compatibilities(self):
        return {
            "success": True,
            "data": [
                {"seal_code": "S-HOC", "pump_tag_number": "110-P-9A"},
                {"seal_code": "S-HSC", "pump_tag_number": "200-P-1A"},
            ],
        }


class TestDocumentScope:
    def test_hoc_document_list_excludes_hsc_seal(self):
        app.dependency_overrides[get_current_user] = lambda: _hoc()
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        app.dependency_overrides[get_seal_engineering_document_gateway] = lambda: FakeDocumentGateway()
        app.dependency_overrides[get_seal_pump_compatibility_gateway] = lambda: FakeCompatGateway()
        try:
            body = client.get("/api/ltsa/documents").json()
            assert body["count"] == 1
            assert body["data"][0]["seal_code"] == "S-HOC"
        finally:
            _clear()

    def test_unrestricted_sees_both(self):
        app.dependency_overrides[get_current_user] = lambda: _identity("JOHN_CRANE_ENGINEER")
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        app.dependency_overrides[get_seal_engineering_document_gateway] = lambda: FakeDocumentGateway()
        app.dependency_overrides[get_seal_pump_compatibility_gateway] = lambda: FakeCompatGateway()
        try:
            assert client.get("/api/ltsa/documents").json()["count"] == 2
        finally:
            _clear()


# --- fleet.py: filter-before-aggregation proof --------------------------

from API.ltsa_knowledge_service import LTSAKnowledge  # noqa: E402
from API.recommendation_engine import Recommendation, PRIORITY_CRITICAL  # noqa: E402


def _knowledge(tag, recommendation=()):
    return LTSAKnowledge(
        tag_number=tag, pump={"tag_number": tag}, seal=[], inventory=[], pm_history=[],
        cm_history=[], breakdown_history=[], drawings=[], recommendation=recommendation,
        pm_schedules=[], condition_monitoring_schedules=[], condition_monitoring_readings=[],
    )


def _recommendation(tag, priority=PRIORITY_CRITICAL, rule_code="REC_TEST"):
    return Recommendation(
        id=f"{rule_code}:{tag}", rule_code=rule_code, priority=priority, category="INSPECTION",
        title="t", description="d", evidence=(), confidence=1.0, action="Inspect",
    )


class _FakeKnowledgeService:
    def build(self, tag):
        return _knowledge(tag)


class _FakeKnowledgeServiceWithCriticalRec:
    def build(self, tag):
        return _knowledge(tag, recommendation=(_recommendation(tag),))


class TestFleetAggregateRecalculation:
    def test_hoc_fleet_reliability_recalculates_pump_count_from_hoc_only(self):
        # Uses the REAL FleetReliabilityService (not a fake) against a
        # fake pump/knowledge layer, proving pump_count is genuinely
        # recomputed from only HOC-visible pumps -- not the full fleet's
        # count with pump names merely hidden afterward.
        from API.fleet_reliability_service import FleetReliabilityService

        service = FleetReliabilityService(pump_gateway=FakePumpGateway(), ltsa_knowledge_service=_FakeKnowledgeService())
        app.dependency_overrides[get_current_user] = lambda: _hoc()
        app.dependency_overrides[get_fleet_reliability_service] = lambda: service
        try:
            body = client.get("/api/ltsa/fleet/reliability").json()
            assert body["data"]["pump_count"] == 1  # only 110-P-9A (HOC), never 3
        finally:
            _clear()

    def test_ma2_fleet_reliability_counts_only_ma2_pumps(self):
        from API.fleet_reliability_service import FleetReliabilityService

        service = FleetReliabilityService(pump_gateway=FakePumpGateway(), ltsa_knowledge_service=_FakeKnowledgeService())
        app.dependency_overrides[get_current_user] = lambda: _ma2()
        app.dependency_overrides[get_fleet_reliability_service] = lambda: service
        try:
            body = client.get("/api/ltsa/fleet/reliability").json()
            assert body["data"]["pump_count"] == 2  # HSC + HCC, never HOC
        finally:
            _clear()

    def test_unrestricted_fleet_reliability_counts_all_pumps(self):
        from API.fleet_reliability_service import FleetReliabilityService

        service = FleetReliabilityService(pump_gateway=FakePumpGateway(), ltsa_knowledge_service=_FakeKnowledgeService())
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        app.dependency_overrides[get_fleet_reliability_service] = lambda: service
        try:
            assert client.get("/api/ltsa/fleet/reliability").json()["data"]["pump_count"] == 3
        finally:
            _clear()

    def test_hoc_powerbi_top_risks_contains_no_hsc_or_hcc_pump(self):
        # Real FleetExecutiveSummaryService + real FleetReliabilityService,
        # against a knowledge layer where EVERY pump (incl. HSC/HCC) has a
        # critical recommendation -- proving top_risks itself, not just
        # pump_count, is recomputed from only in-scope pumps.
        from API.fleet_reliability_service import FleetReliabilityService
        from API.fleet_executive_summary import FleetExecutiveSummaryService

        reliability_service = FleetReliabilityService(
            pump_gateway=FakePumpGateway(), ltsa_knowledge_service=_FakeKnowledgeServiceWithCriticalRec()
        )
        summary_service = FleetExecutiveSummaryService(fleet_reliability_service=reliability_service)

        app.dependency_overrides[get_current_user] = lambda: _hoc()
        app.dependency_overrides[get_fleet_executive_summary_service] = lambda: summary_service
        try:
            body = client.get("/api/ltsa/fleet/powerbi").json()
            tags_in_top_risks = {r["tag_number"] for r in body["data"]["top_risks"]}
            assert tags_in_top_risks == {"110-P-9A"}
            assert "200-P-1A" not in tags_in_top_risks
            assert "300-P-1A" not in tags_in_top_risks
            assert body["data"]["critical_asset_count"] == 1  # never 3
        finally:
            _clear()


# --- copilot.py: filter-before-aggregation proof -------------------------


class FakeWorkOrderGateway:
    def list_work_orders(self):
        return {"success": True, "data": [
            {"work_order_code": "WO-HOC", "asset_code": "110-P-9A", "asset_type": "PUMP", "closed_at": None},
            {"work_order_code": "WO-HSC", "asset_code": "200-P-1A", "asset_type": "PUMP", "closed_at": None},
        ]}


class FakeMaintenanceHistoryGateway:
    def list_maintenance_history(self):
        return {"success": True, "data": []}


class TestCopilotRouterPassesScopeThrough:
    def test_router_calls_summarize_maintenance_situation_with_the_resolved_scope(self):
        # Mirrors test_main.py's own test_copilot_summary_delegates_to_
        # maintenance_copilot pattern (patches the imported function
        # directly -- get_organization() needs a real filesystem Company
        # artifact this test suite doesn't construct). Proves the router
        # itself resolves and forwards scope; the actual filtering logic
        # is proven separately below at the service layer.
        from unittest.mock import patch

        app.dependency_overrides[get_current_user] = lambda: _hoc()
        try:
            with patch(
                "routers.copilot._summarize_maintenance_situation",
                return_value={"message": "ok", "data": {}},
            ) as mock_fn:
                response = client.get("/copilot/summary")
            assert response.status_code == 200
            _, kwargs = mock_fn.call_args
            assert kwargs["scope"] == frozenset({"HOC"})
        finally:
            _clear()

    def test_unrestricted_role_passes_none_scope(self):
        from unittest.mock import patch

        app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
        try:
            with patch(
                "routers.copilot._summarize_maintenance_situation",
                return_value={"message": "ok", "data": {}},
            ) as mock_fn:
                client.get("/copilot/summary")
            _, kwargs = mock_fn.call_args
            assert kwargs["scope"] is None
        finally:
            _clear()


def _seed_organization(tmp_path, product_name="LTSA-BRAIN"):
    # Mirrors CORE-SERVICES/API/TESTS/test_maintenance_command_center.py's
    # own proven fixture -- get_maintenance_command_center() calls the
    # real get_organization(), which needs a real Company artifact on
    # disk under root_path, not a mock.
    from API.company_manufacturing import manufacture_company
    from API.department_manufacturing import manufacture_department
    from API.role_manufacturing import manufacture_role

    product_dir = tmp_path / "PRODUCTS" / product_name
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "product_artifact.json").write_text("{}", encoding="utf-8")
    manufacture_company(product_name=product_name, company_name="Test Co", root_path=tmp_path)
    manufacture_department(product_name=product_name, department_name="Ops", root_path=tmp_path)
    manufacture_role(product_name=product_name, role_name="Tech", department_name="Ops", root_path=tmp_path)


class TestMaintenanceCommandCenterFiltersBeforeAggregation:
    def test_hoc_scope_recomputes_counts_and_recent_lists_from_hoc_only(self, tmp_path):
        from API.maintenance_command_center import get_maintenance_command_center

        _seed_organization(tmp_path)
        result = get_maintenance_command_center(
            "LTSA-BRAIN",
            root_path=tmp_path,
            pump_gateway=FakePumpGateway(),
            work_order_gateway=FakeWorkOrderGateway(),
            maintenance_history_gateway=FakeMaintenanceHistoryGateway(),
            scope=frozenset({"HOC"}),
        )
        assert result["summary"]["total_pumps"] == 1
        assert result["summary"]["active_work_orders"] == 1
        work_order_pumps = {wo["pump"] for wo in result["recent_work_orders"]}
        assert work_order_pumps == {"110-P-9A"}  # never leaks 200-P-1A

    def test_unrestricted_scope_none_sees_everything_unchanged(self, tmp_path):
        from API.maintenance_command_center import get_maintenance_command_center

        _seed_organization(tmp_path)
        result = get_maintenance_command_center(
            "LTSA-BRAIN",
            root_path=tmp_path,
            pump_gateway=FakePumpGateway(),
            work_order_gateway=FakeWorkOrderGateway(),
            maintenance_history_gateway=FakeMaintenanceHistoryGateway(),
            scope=None,
        )
        assert result["summary"]["total_pumps"] == 3
        assert result["summary"]["active_work_orders"] == 2
