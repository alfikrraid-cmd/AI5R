"""MWO-AI5R-LTSA-COPILOT-001 -- proves POST /api/ltsa/copilot/ask enforces
the same permission/area-scope discipline as every other LTSA route, never
infers a seal from a sister asset, and never fabricates an answer when
data is missing (DATA_GAP instead of a guess).
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
    get_copilot_ai_client,
    get_current_user,
    get_equipment_timeline_service,
    get_installation_gateway,
    get_ltsa_knowledge_service,
    get_maintenance_history_gateway,
    get_pump_gateway,
    get_work_order_gateway,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402
from API.ltsa_knowledge_service import LTSAKnowledge  # noqa: E402
from API.equipment_timeline_service import PumpLifecycleCurrentSeal  # noqa: E402
from API.recommendation_engine import Evidence, Recommendation  # noqa: E402

client = TestClient(app)

_PUMPS = {
    "940-P-2A": {"tag_number": "940-P-2A", "area": "HOC", "status": "RUNNING"},
    "940-P-2B": {"tag_number": "940-P-2B", "area": "HOC", "status": "STANDBY"},
    "600-P-1A": {"tag_number": "600-P-1A", "area": "UTL", "status": "RUNNING"},
}

# One current seal per tag, deliberately distinct, to prove the endpoint
# never answers pump A's question with pump B's seal.
_CURRENT_SEALS = {
    "940-P-2A": PumpLifecycleCurrentSeal(
        seal_code="SEAL-A-DE", seal_name="Seal A", manufacturer="JC", model="M1",
        shaft_size="45mm", material="316SS", temperature_limit=120, pressure_limit=16,
        status="ACTIVE", installation_code="INST-A-1", installed_at="2024-01-01", source="seal_registry",
    ),
    "940-P-2B": PumpLifecycleCurrentSeal(
        seal_code="SEAL-B-NDE", seal_name="Seal B", manufacturer="JC", model="M2",
        shaft_size="50mm", material="316SS", temperature_limit=120, pressure_limit=16,
        status="ACTIVE", installation_code="INST-B-1", installed_at="2024-02-01", source="seal_registry",
    ),
}


class FakePumpGateway:
    def get_pump(self, tag_number):
        match = _PUMPS.get(tag_number)
        if match is None:
            return {"success": False, "message": "not found", "data": None}
        return {"success": True, "message": "ok", "data": match}

    def list_pumps(self):
        return {"success": True, "message": "ok", "data": list(_PUMPS.values())}


class FakeMaintenanceHistoryGateway:
    def list_maintenance_history(self):
        return {"success": True, "data": []}


class FakeWorkOrderGateway:
    def list_work_orders(self):
        return {
            "success": True,
            "data": [
                {"work_order_code": "WO-1", "asset_code": "940-P-2A", "status": "OPEN", "closed_at": None},
                {"work_order_code": "WO-2", "asset_code": "600-P-1A", "status": "OPEN", "closed_at": None},
            ],
        }


class FakeInstallationGateway:
    def list_installations(self):
        return {"success": True, "data": []}


class FakeLTSAKnowledgeService:
    def build(self, tag_number):
        recommendation = ()
        if tag_number == "940-P-2A":
            recommendation = (
                Recommendation(
                    id=f"REC_CRITICAL_CM:{tag_number}", rule_code="REC_CRITICAL_CM", priority=100,
                    category="INSPECTION", title="Immediate Inspection", description="desc",
                    evidence=(Evidence(source="CMReport", reference="CM-1", field="severity", value="CRITICAL"),),
                    confidence=1.0, action="Inspect now.",
                ),
            )
        return LTSAKnowledge(
            tag_number=tag_number, pump=_PUMPS.get(tag_number), seal=[], inventory=[],
            pm_history=[], cm_history=[], breakdown_history=[], drawings=[],
            recommendation=recommendation, pm_schedules=[], condition_monitoring_schedules=[],
            condition_monitoring_readings=[],
        )


class FakeEquipmentTimelineService:
    def build_current_seal(self, tag_number):
        return _CURRENT_SEALS.get(tag_number)


def _identity(role: str, *, data_scope_type=None, data_scope_value=None, permissions=None) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id="u1", email="u1@example.test", organization_id="org-1",
        organization_code="PERTAMINA_RU_II", role=role,
        permissions=ROLE_PERMISSIONS[role] if permissions is None else permissions,
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


def _as(identity: AuthenticatedIdentity):
    app.dependency_overrides[get_current_user] = lambda: identity
    # MWO-AI5R-LTSA-AI-ORCHESTRATION-001 -- these router tests exercise the
    # pre-existing DETERMINISTIC path specifically; ai_client=None makes
    # orchestrate_copilot() skip the AI path deterministically (see its own
    # docstring) instead of depending on whether a real Ollama daemon
    # happens to be reachable on this machine. The AI-selected/multi-tool/
    # fallback paths are covered by TESTS/test_copilot_orchestrator.py with
    # a mocked AI client.
    app.dependency_overrides[get_copilot_ai_client] = lambda: None
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    app.dependency_overrides[get_maintenance_history_gateway] = lambda: FakeMaintenanceHistoryGateway()
    app.dependency_overrides[get_work_order_gateway] = lambda: FakeWorkOrderGateway()
    app.dependency_overrides[get_installation_gateway] = lambda: FakeInstallationGateway()
    app.dependency_overrides[get_ltsa_knowledge_service] = lambda: FakeLTSAKnowledgeService()
    app.dependency_overrides[get_equipment_timeline_service] = lambda: FakeEquipmentTimelineService()


def _clear():
    for dep in (
        get_current_user, get_copilot_ai_client, get_pump_gateway, get_maintenance_history_gateway,
        get_work_order_gateway, get_installation_gateway, get_ltsa_knowledge_service,
        get_equipment_timeline_service,
    ):
        app.dependency_overrides.pop(dep, None)


def _ask(question, asset_context=None):
    return client.post("/api/ltsa/copilot/ask", json={"question": question, "asset_context": asset_context})


class TestAuth:
    def test_missing_bearer_token_is_401(self):
        response = client.post("/api/ltsa/copilot/ask", json={"question": "status"})
        assert response.status_code == 401

    def test_missing_permission_is_403(self):
        _as(_identity("PERTAMINA_VIEWER", permissions=frozenset()))
        try:
            response = _ask("status", "940-P-2A")
            assert response.status_code == 403
        finally:
            _clear()


class TestAreaScope:
    def test_in_scope_tag_is_answered(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"))
        try:
            response = _ask("what is the pump status?", "940-P-2A")
            assert response.status_code == 200
            assert response.json()["kind"] == "FACT"
        finally:
            _clear()

    def test_out_of_scope_tag_is_404_not_a_distinct_status(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"))
        try:
            out_of_scope = _ask("what is the pump status?", "600-P-1A")  # real tag, wrong area
            genuinely_missing = _ask("what is the pump status?", "NOT-A-REAL-TAG")
            assert out_of_scope.status_code == genuinely_missing.status_code == 404
        finally:
            _clear()

    def test_unrestricted_role_reaches_any_tag(self):
        _as(_identity("TAP_ADMIN"))
        try:
            assert _ask("status", "600-P-1A").status_code == 200
        finally:
            _clear()


class TestIntents:
    def setup_method(self):
        _as(_identity("TAP_ADMIN"))

    def teardown_method(self):
        _clear()

    def test_pump_status_question(self):
        body = _ask("What is the current status?", "940-P-2A").json()
        assert body["kind"] == "FACT"
        assert "RUNNING" in body["answer"]

    def test_asset_context_question_current_seal(self):
        # Mirrors the MWO's own example: asset context is auto-attached
        # (workspace selection), question is free text.
        body = _ask("seal terakhir apa?", "940-P-2A").json()
        assert body["kind"] == "FACT"
        assert "SEAL-A-DE" in body["answer"]

    def test_recommendation_intent(self):
        body = _ask("any recommendation?", "940-P-2A").json()
        assert body["kind"] == "RECOMMENDATION"
        assert "REC" not in body["answer"] or "Immediate Inspection" in body["answer"]

    def test_pump_history_question_with_no_records_is_still_fact(self):
        body = _ask("what is the maintenance history?", "940-P-2A").json()
        assert body["kind"] == "FACT"
        assert "No maintenance history" in body["answer"]

    def test_global_work_orders_question_needs_no_asset(self):
        body = _ask("show active work orders").json()
        assert body["kind"] == "FACT"
        assert "WO-1" in body["answer"] and "WO-2" in body["answer"]

    def test_unsupported_question_is_data_gap(self):
        body = _ask("what's the weather today?", "940-P-2A").json()
        assert body["kind"] == "DATA_GAP"

    def test_asset_scoped_question_with_no_asset_context_is_data_gap(self):
        body = _ask("what is the pump status?").json()
        assert body["kind"] == "DATA_GAP"

    def test_missing_current_seal_evidence_is_data_gap_not_fabricated(self):
        body = _ask("what is the current seal?", "600-P-1A").json()  # no seal record faked for this tag
        assert body["kind"] == "DATA_GAP"


class TestIdentitySafety:
    def setup_method(self):
        _as(_identity("TAP_ADMIN"))

    def teardown_method(self):
        _clear()

    def test_no_sister_pump_inference(self):
        answer_a = _ask("seal terakhir apa?", "940-P-2A").json()["answer"]
        answer_b = _ask("seal terakhir apa?", "940-P-2B").json()["answer"]
        assert "SEAL-A-DE" in answer_a and "SEAL-B-NDE" not in answer_a
        assert "SEAL-B-NDE" in answer_b and "SEAL-A-DE" not in answer_b

    def test_de_nde_is_a_seal_attribute_not_a_separate_asset(self):
        # Both DE- and NDE-suffixed seal_codes above belong to the SAME
        # per-tag lookup path (build_current_seal(tag)) -- proving the
        # endpoint never branches on DE/NDE as if it were a second tag.
        response = _ask("seal terakhir apa?", "940-P-2A")
        assert response.status_code == 200
        assert response.json()["evidence"][0]["value"] == "SEAL-A-DE"


class FakeAIClient:
    """Deterministic stand-in for EngineeringAIClient -- no network call.
    `responses` is consumed in order, one per generate_json() call."""

    def __init__(self, responses):
        self._responses = list(responses)

    def generate_json(self, prompt, *, system_prompt="", temperature=0.2):
        return self._responses.pop(0)


class TestAIOrchestrationThroughRouter:
    """Proves the AI path is reachable through the real endpoint (not just
    the orchestrator unit tests), and that scope/auth are enforced BEFORE
    any AI call -- an out-of-scope tag must never reach the AI client."""

    def teardown_method(self):
        _clear()
        app.dependency_overrides.pop(get_copilot_ai_client, None)

    def test_ai_path_returns_tools_used_and_combined_evidence(self):
        _as(_identity("TAP_ADMIN"))
        app.dependency_overrides[get_copilot_ai_client] = lambda: FakeAIClient(
            [
                {"tools": ["pump_status", "current_seal"]},
                {"answer": "940-P-2A is RUNNING with seal SEAL-A-DE installed.", "kind": "INTERPRETATION"},
            ]
        )
        body = _ask("Analisa 940-P-2A, apa yang perlu saya perhatikan?", "940-P-2A").json()
        assert sorted(body["tools_used"]) == ["current_seal", "pump_status"]
        assert len(body["evidence"]) == 2
        assert body["kind"] == "INTERPRETATION"

    def test_out_of_scope_tag_never_reaches_ai_client(self):
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"))

        class ExplodingAIClient:
            def generate_json(self, *_a, **_kw):
                raise AssertionError("AI client must not be called for an out-of-scope tag")

        app.dependency_overrides[get_copilot_ai_client] = lambda: ExplodingAIClient()
        response = _ask("status", "600-P-1A")  # real tag, wrong area -- scope guard runs first
        assert response.status_code == 404
