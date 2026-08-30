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
    get_cm_report_repository,
    get_condition_monitoring_reading_gateway,
    get_condition_monitoring_reading_repository,
    get_copilot_ai_client,
    get_current_user,
    get_equipment_timeline_service,
    get_fleet_executive_summary_service,
    get_installation_gateway,
    get_installation_report_repository,
    get_ltsa_knowledge_service,
    get_maintenance_history_gateway,
    get_mechanical_seal_stock_repository,
    get_pm_occurrence_repository,
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
    # MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017 -- optional `records`
    # (default [], byte-for-byte the pre-existing behavior every prior test
    # already relies on) lets the new fleet-installation tests supply real
    # records without touching any existing call site.
    def __init__(self, records=None):
        self._records = records if records is not None else []

    def list_installations(self):
        return {"success": True, "data": self._records}


class FakeInstallationReportRepository:
    def __init__(self, records=None):
        self._records = records if records is not None else []

    def list_installations(self):
        return {"success": True, "data": self._records}


class FakeMechanicalSealStockRepository:
    def __init__(self, records=None):
        self._records = records if records is not None else []

    def list_pools(self, **_kwargs):
        return {"success": True, "items": self._records, "data": self._records}


class FakeConditionMonitoringReadingGateway:
    def __init__(self, records=None):
        self._records = records if records is not None else []

    def list_condition_monitoring_readings(self):
        return {"success": True, "data": self._records}


class FakeConditionMonitoringReadingRepository:
    def __init__(self, readings_by_asset=None):
        self._readings_by_asset = readings_by_asset or {}

    def list_by_asset(self, asset_code):
        return list(self._readings_by_asset.get(asset_code, []))


class FakePMOccurrenceRepository:
    def __init__(self, occurrences_by_asset=None):
        self._occurrences_by_asset = occurrences_by_asset or {}

    def list_by_asset(self, asset_code):
        return list(self._occurrences_by_asset.get(asset_code, []))


class FakeCMReportRepository:
    def __init__(self, records=None, *, success=True):
        self._records = records if records is not None else []
        self._success = success

    def list_cm_reports(self, **_kwargs):
        return {"success": self._success, "data": self._records}


class _FakeTopRisk:
    def __init__(self, tag_number, title, priority, action):
        self.tag_number = tag_number
        self.title = title
        self.priority = priority
        self.action = action


class _FakeFleetExecutiveSummary:
    def __init__(self, *, fleet_status="NORMAL", top_risks=()):
        self.fleet_status = fleet_status
        self.top_risks = top_risks


class FakeFleetExecutiveSummaryService:
    def __init__(self, summary=None):
        self._summary = summary if summary is not None else _FakeFleetExecutiveSummary()
        self.build_calls = []

    def build(self, *, scope=None):
        self.build_calls.append(scope)
        return self._summary


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
    app.dependency_overrides[get_installation_report_repository] = lambda: FakeInstallationReportRepository()
    app.dependency_overrides[get_mechanical_seal_stock_repository] = lambda: FakeMechanicalSealStockRepository()
    app.dependency_overrides[get_condition_monitoring_reading_gateway] = lambda: FakeConditionMonitoringReadingGateway()
    app.dependency_overrides[get_condition_monitoring_reading_repository] = lambda: FakeConditionMonitoringReadingRepository()
    app.dependency_overrides[get_fleet_executive_summary_service] = lambda: FakeFleetExecutiveSummaryService()
    app.dependency_overrides[get_pm_occurrence_repository] = lambda: FakePMOccurrenceRepository()
    app.dependency_overrides[get_cm_report_repository] = lambda: FakeCMReportRepository()


def _clear():
    for dep in (
        get_current_user, get_copilot_ai_client, get_pump_gateway, get_maintenance_history_gateway,
        get_work_order_gateway, get_installation_gateway, get_ltsa_knowledge_service,
        get_equipment_timeline_service, get_condition_monitoring_reading_gateway,
        get_installation_report_repository, get_mechanical_seal_stock_repository,
        get_condition_monitoring_reading_repository, get_fleet_executive_summary_service,
        get_pm_occurrence_repository, get_cm_report_repository,
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

    def test_fleet_priority_query_passes_caller_scope_into_canonical_build(self):
        # Phase 2's own requirement: the canonical query itself must
        # operate on authorized scope, not a global ranking filtered
        # afterward -- proven here by asserting the EXACT scope this
        # scoped identity resolves to is what reaches
        # FleetExecutiveSummaryService.build(), through the real router,
        # not a hand-constructed frozenset in a unit test.
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"))
        service = FakeFleetExecutiveSummaryService()
        app.dependency_overrides[get_fleet_executive_summary_service] = lambda: service
        try:
            response = _ask("pompa mana yang perlu perhatian hari ini?")
            assert response.status_code == 200
            assert service.build_calls == [frozenset({"HOC"})]
        finally:
            _clear()

    def test_unrestricted_role_fleet_priority_scope_is_none(self):
        _as(_identity("TAP_ADMIN"))
        service = FakeFleetExecutiveSummaryService()
        app.dependency_overrides[get_fleet_executive_summary_service] = lambda: service
        try:
            _ask("pompa mana yang perlu perhatian hari ini?")
            assert service.build_calls == [None]
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

    def test_tag_scoped_condition_monitoring_question(self):
        app.dependency_overrides[get_condition_monitoring_reading_repository] = lambda: FakeConditionMonitoringReadingRepository(
            {"940-P-2A": [{"condition_monitoring_reading_code": "CMONR-1", "reading_date": "2026-08-30", "finding": "Kebocoran mechanical seal"}]}
        )
        body = _ask("ada temuan terbaru?", "940-P-2A").json()
        assert body["kind"] == "FACT"
        assert "Kebocoran mechanical seal" in body["answer"]

    def test_tag_scoped_condition_monitoring_no_data_is_truthful(self):
        # Dashboard uses the endpoint's own default language ("en") -- WhatsApp
        # is the only caller that requests "id" (MWO-LTSA-WHATSAPP-ID-LANGUAGE-001).
        body = _ask("CMON terakhir apa?", "940-P-2A").json()  # default FakeConditionMonitoringReadingRepository: empty
        assert body["kind"] == "FACT"
        assert "No Condition Monitoring data found" in body["answer"]

    def test_fleet_priority_question_needs_no_asset(self):
        app.dependency_overrides[get_fleet_executive_summary_service] = lambda: FakeFleetExecutiveSummaryService(
            _FakeFleetExecutiveSummary(
                fleet_status="ATTENTION",
                top_risks=(_FakeTopRisk("940-P-2A", "Vibration trending high", 120, "Schedule CM inspection"),),
            )
        )
        body = _ask("pompa mana yang perlu perhatian hari ini?").json()
        assert body["kind"] == "RECOMMENDATION"
        assert "940-P-2A" in body["answer"]


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
        self.calls = []

    def generate_json(self, prompt, *, system_prompt="", temperature=0.2):
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "temperature": temperature})
        return self._responses.pop(0)


class TestInferredExactContext:
    def setup_method(self):
        _as(_identity("TAP_ADMIN"))

    def teardown_method(self):
        _clear()

    def _ai(self):
        ai = FakeAIClient([
            {"tools": ["pump_status"]},
            {"answer": "940-P-2A is RUNNING.", "kind": "FACT"},
        ])
        app.dependency_overrides[get_copilot_ai_client] = lambda: ai
        return ai

    def test_question_tag_resolves_exact_context_before_ai(self):
        ai = self._ai()
        response = _ask("Analisa 940-P-2A")
        assert response.status_code == 200
        assert response.json()["tools_used"] == ["pump_status"]
        assert len(ai.calls) == 2
        assert "asset 940-P-2A" in ai.calls[0]["prompt"]
        assert "940-P-2B" not in ai.calls[0]["prompt"]

    def test_existing_asset_context_is_preserved(self):
        ai = self._ai()
        response = _ask("Analisa this pump", "940-P-2A")
        assert response.status_code == 200
        assert "asset 940-P-2A" in ai.calls[0]["prompt"]

    def test_unknown_inferred_tag_is_safe_404_and_never_reaches_ai(self):
        class ExplodingAI:
            def generate_json(self, *_args, **_kwargs):
                raise AssertionError("AI must not run for an unknown inferred tag")

        app.dependency_overrides[get_copilot_ai_client] = lambda: ExplodingAI()
        response = _ask("Analisa 999-P-9A")
        assert response.status_code == 404
        assert response.json()["detail"] == "Pump not found"

    def test_out_of_scope_inferred_tag_is_safe_404(self):
        class ExplodingAI:
            def generate_json(self, *_args, **_kwargs):
                raise AssertionError("AI must not run for an out-of-scope inferred tag")

        _clear()
        _as(_identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC"))
        app.dependency_overrides[get_copilot_ai_client] = lambda: ExplodingAI()
        response = _ask("Analisa 600-P-1A")
        assert response.status_code == 404
        assert response.json()["detail"] == "Pump not found"

    def test_multiple_tags_are_not_guessed_or_sent_to_ai(self):
        class ExplodingAI:
            def generate_json(self, *_args, **_kwargs):
                raise AssertionError("AI must not run for ambiguous tags")

        app.dependency_overrides[get_copilot_ai_client] = lambda: ExplodingAI()
        response = _ask("Compare 940-P-2A with 940-P-2B")
        assert response.status_code == 200
        assert response.json()["kind"] == "DATA_GAP"
        assert "multiple pump tags" in response.json()["answer"]

    def test_de_nde_text_does_not_change_exact_pump_identity(self):
        ai = self._ai()
        response = _ask("Analisa 940-P-2A DE/NDE")
        assert response.status_code == 200
        assert "asset 940-P-2A" in ai.calls[0]["prompt"]
        assert "940-P-2B" not in ai.calls[0]["prompt"]

    def test_tagless_question_keeps_existing_deterministic_behavior(self):
        class ExplodingAI:
            def generate_json(self, *_args, **_kwargs):
                raise AssertionError("AI must not run without a tag")

        app.dependency_overrides[get_copilot_ai_client] = lambda: ExplodingAI()
        response = _ask("what is the weather today?")
        assert response.status_code == 200
        assert response.json()["kind"] == "DATA_GAP"

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
