"""MWO-AI5R-LTSA-AI-ORCHESTRATION-001 -- unit tests for
copilot_orchestrator.orchestrate_copilot(), isolated from FastAPI/HTTP
(router-level auth/scope/tools_used integration is covered separately in
CORE-SERVICES/BACKEND-API/TESTS/test_copilot_ask_router.py's
TestAIOrchestrationThroughRouter). No network call anywhere in this file --
the AI client is always a controllable fake.
"""

import sys
from pathlib import Path

CORE_SERVICES_DIR = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_DIR))

from API.copilot_ask_service import CopilotAnswer, DATA_GAP, FACT  # noqa: E402
from API.copilot_orchestrator import MAX_TOOLS_PER_REQUEST, orchestrate_copilot  # noqa: E402


class FakeAIClient:
    """`responses` is consumed in call order; a response that is an
    exception INSTANCE is raised instead of returned (simulates a
    provider timeout/error mid-sequence)."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def generate_json(self, prompt, *, system_prompt="", temperature=0.2):
        self.calls.append(prompt)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _pump_status_ok(tag="940-P-2A"):
    return {"success": True, "data": {"tag_number": tag, "status": "RUNNING", "pump_type": "Centrifugal", "area": "HOC"}}


class FakePumpGateway:
    def get_pump(self, tag_number):
        return _pump_status_ok(tag_number)


def _deps(**overrides):
    base = dict(
        pump_gateway=FakePumpGateway(),
        maintenance_history_gateway=None,
        work_order_gateway=None,
        installation_gateway=None,
        ltsa_knowledge_service=None,
        equipment_timeline_service=None,
        # MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017 -- two new
        # tag-optional fleet intents (installation/latest,
        # condition_monitoring/leak-frequency) need these; every existing
        # test below exercises a tagged intent that never reads them.
        seal_stock_gateway=None,
        condition_monitoring_reading_gateway=None,
    )
    base.update(overrides)
    return base


class TestDeterministicPaths:
    def test_no_ai_client_is_deterministic(self):
        answer, tools_used = orchestrate_copilot("what is the status?", "940-P-2A", None, None, **_deps())
        assert answer.kind == FACT
        assert tools_used == []

    def test_no_tag_is_deterministic_even_with_ai_client(self):
        # Global/tag-less question: existing deterministic dispatcher
        # (scope-filtered global work-orders / DATA_GAP) handles it --
        # never routed through the AI path.
        client = FakeAIClient([{"tools": ["pump_status"]}])
        answer, tools_used = orchestrate_copilot("what is the status?", None, None, client, **_deps())
        assert answer.kind == DATA_GAP
        assert tools_used == []
        assert client.calls == []  # never invoked


class TestAIRouting:
    def test_natural_language_question_routes_through_ai(self):
        client = FakeAIClient(
            [
                {"tools": ["pump_status"]},
                {"answer": "940-P-2A is running normally.", "kind": "FACT"},
            ]
        )
        answer, tools_used = orchestrate_copilot(
            "Analisa 940-P-2A, apa yang perlu saya perhatikan?", "940-P-2A", None, client, **_deps()
        )
        assert tools_used == ["pump_status"]
        assert answer.answer == "940-P-2A is running normally."
        assert answer.kind == FACT
        assert len(answer.evidence) == 1

    def test_multi_tool_question_combines_evidence(self):
        client = FakeAIClient(
            [
                {"tools": ["pump_status", "cm"]},
                {"answer": "Status RUNNING; no CM record found.", "kind": "INTERPRETATION"},
            ]
        )

        def fake_get_pump_last_cm(tag):
            return {"success": True, "last_cm": None}

        import API.copilot_ask_service as svc

        original = svc.mis.get_pump_last_cm
        svc.mis.get_pump_last_cm = fake_get_pump_last_cm
        try:
            answer, tools_used = orchestrate_copilot("full analysis please", "940-P-2A", None, client, **_deps())
        finally:
            svc.mis.get_pump_last_cm = original

        assert sorted(tools_used) == ["cm", "pump_status"]
        assert answer.kind == "INTERPRETATION"
        assert len(answer.evidence) == 1  # pump_status contributes evidence; the empty CM does not

    def test_unrecognized_tool_name_is_silently_dropped_never_executed(self):
        # Proves there is no path from an LLM response to arbitrary code --
        # only names already in TOOL_CATALOG/TOOL_HANDLERS ever run.
        client = FakeAIClient(
            [
                {"tools": ["pump_status", "raw_sql", "DROP TABLE pumps"]},
                {"answer": "Status only.", "kind": "FACT"},
            ]
        )
        answer, tools_used = orchestrate_copilot("status please", "940-P-2A", None, client, **_deps())
        assert tools_used == ["pump_status"]

    def test_tool_selection_is_capped(self):
        many_tools = ["pump_status", "pump_history", "work_orders", "pm", "cm", "current_seal", "seal_compat"]
        assert len(many_tools) > MAX_TOOLS_PER_REQUEST
        client = FakeAIClient([{"tools": many_tools}, {"answer": "ok", "kind": "FACT"}])
        _answer, tools_used = orchestrate_copilot("everything please", "940-P-2A", None, client, **_deps())
        assert len(tools_used) <= MAX_TOOLS_PER_REQUEST


class TestFallback:
    def test_provider_error_falls_back_to_deterministic(self):
        client = FakeAIClient([RuntimeError("connection refused")])
        answer, tools_used = orchestrate_copilot("what is the status?", "940-P-2A", None, client, **_deps())
        assert tools_used == []
        assert answer.kind == FACT
        assert "RUNNING" in answer.answer

    def test_provider_timeout_falls_back_to_deterministic(self):
        client = FakeAIClient([TimeoutError("timed out")])
        answer, tools_used = orchestrate_copilot("what is the status?", "940-P-2A", None, client, **_deps())
        assert tools_used == []
        assert answer.kind == FACT

    def test_malformed_tool_selection_json_falls_back(self):
        client = FakeAIClient(["not-a-json-object-but-a-plain-string"])
        answer, tools_used = orchestrate_copilot("what is the status?", "940-P-2A", None, client, **_deps())
        assert tools_used == []
        assert answer.kind == FACT

    def test_synthesis_returning_no_answer_falls_back(self):
        client = FakeAIClient([{"tools": ["pump_status"]}, {"kind": "FACT"}])  # missing "answer"
        answer, tools_used = orchestrate_copilot("what is the status?", "940-P-2A", None, client, **_deps())
        assert tools_used == []
        assert answer.kind == FACT

    def test_no_tools_selected_falls_back(self):
        client = FakeAIClient([{"tools": []}])
        answer, tools_used = orchestrate_copilot("what is the status?", "940-P-2A", None, client, **_deps())
        assert tools_used == []
        assert answer.kind == FACT


class TestEngineeringSafety:
    def test_data_gap_forced_when_no_tool_produced_evidence(self):
        # current_seal returns DATA_GAP (no evidence) when
        # equipment_timeline_service.build_current_seal() returns None --
        # even if the LLM's own synthesis claims FACT, the forced
        # evidence-empty guard must win.
        class NoSealTimelineService:
            def build_current_seal(self, tag_number):
                return None

        client = FakeAIClient(
            [
                {"tools": ["current_seal"]},
                {"answer": "The seal is definitely SEAL-X.", "kind": "FACT"},  # LLM overclaiming
            ]
        )
        answer, tools_used = orchestrate_copilot(
            "seal terakhir apa?", "940-P-2A", None, client,
            **_deps(equipment_timeline_service=NoSealTimelineService()),
        )
        assert tools_used == ["current_seal"]
        assert answer.kind == DATA_GAP  # forced, not the LLM's claimed FACT
        assert answer.evidence == ()

    def test_no_sister_pump_inference_across_two_tags(self):
        class TimelineService:
            def build_current_seal(self, tag_number):
                from dataclasses import dataclass

                @dataclass
                class Seal:
                    seal_code: str
                    seal_name: str = "Seal"
                    installed_at: str = "2024-01-01"
                    source: str = "seal_registry"
                    installation_code: str = "INST-1"

                return Seal(seal_code="SEAL-A" if tag_number == "940-P-2A" else "SEAL-B")

        client = FakeAIClient(
            [
                {"tools": ["current_seal"]}, {"answer": "seal a", "kind": FACT},
                {"tools": ["current_seal"]}, {"answer": "seal b", "kind": FACT},
            ]
        )
        deps = _deps(equipment_timeline_service=TimelineService())
        answer_a, _ = orchestrate_copilot("seal terakhir apa?", "940-P-2A", None, client, **deps)
        answer_b, _ = orchestrate_copilot("seal terakhir apa?", "940-P-2B", None, client, **deps)
        assert answer_a.evidence[0]["value"] == "SEAL-A"
        assert answer_b.evidence[0]["value"] == "SEAL-B"
