import dataclasses

from API.ltsa_messaging_gateway import LTSAMessagingGateway, MessageRequest, MessageResponse
from API.ltsa_knowledge_service import LTSAKnowledge
from API.recommendation_engine import Recommendation
from API.fleet_executive_summary import FleetExecutiveSummary, TopRisk

# MWO-LTSA-039A -- LTSAMessagingGateway: a channel-agnostic orchestration
# foundation over already-existing services, reused in-process exactly as
# pumps.py's get_ltsa_pump_knowledge and fleet.py's get_fleet_powerbi
# already compose them -- no HTTP client, no SQL, no WhatsApp SDK, no new
# calculation, no new formatting. Fakes below stand in for
# LTSAKnowledgeService / EngineeringContextEngine / FleetExecutiveSummaryService
# so these tests exercise only the Gateway's own orchestration, never
# re-deriving what those services (or build_engineering_insight /
# build_fleet_insight) already cover in their own test files.


class FakeKnowledgeService:
    def __init__(self, by_tag):
        self._by_tag = by_tag
        self.calls = []

    def build(self, tag_number):
        self.calls.append(tag_number)
        return self._by_tag[tag_number]


class FakeContextEngine:
    def __init__(self, by_tag):
        self._by_tag = by_tag
        self.calls = []

    def build(self, tag_number):
        self.calls.append(tag_number)
        return self._by_tag[tag_number]


class FakeFleetExecutiveSummaryService:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def build(self):
        self.calls += 1
        return self.result


def _recommendation(**overrides):
    defaults = dict(
        id="REC_CRITICAL_CM:P-1",
        rule_code="REC_CRITICAL_CM",
        priority=100,
        category="INSPECTION",
        title="Immediate Inspection",
        description="An open Corrective Maintenance report with critical or major severity was found.",
        evidence=(),
        confidence=1.0,
        action="Dispatch a technician for immediate inspection.",
    )
    defaults.update(overrides)
    return Recommendation(**defaults)


def _knowledge(tag, recommendation=()):
    return LTSAKnowledge(
        tag_number=tag,
        pump={"tag_number": tag, "pump_name": "Main Feed Pump"},
        seal=[],
        inventory=[],
        pm_history=[],
        cm_history=[],
        breakdown_history=[],
        drawings=[],
        recommendation=recommendation,
        pm_schedules=[],
        condition_monitoring_schedules=[],
    )


def _summary(**overrides):
    defaults = {"asset": {"tag_number": "P-1"}, "cm_summary": {"overall_condition": "CRITICAL"}}
    defaults.update(overrides)
    return defaults


def _top_risk(**overrides):
    defaults = dict(
        tag_number="P-1",
        rule_code="REC_CRITICAL_CM",
        title="Immediate Inspection",
        priority=100,
        action="Dispatch a technician for immediate inspection.",
        description="An open Corrective Maintenance report with critical or major severity was found.",
    )
    defaults.update(overrides)
    return TopRisk(**defaults)


def _fleet_summary(**overrides):
    defaults = dict(
        overall_health=55.0,
        fleet_status="ATTENTION",
        critical_asset_count=1,
        fleet_availability=98.5,
        fleet_mtbf_days=42.3,
        fleet_mttr_hours=6.25,
        breakdown_count=2,
        critical_spare_count=0,
        top_risks=(_top_risk(),),
    )
    defaults.update(overrides)
    return FleetExecutiveSummary(**defaults)


def _gateway(knowledge_by_tag=None, context_by_tag=None, fleet_summary=None):
    knowledge_service = FakeKnowledgeService(knowledge_by_tag or {})
    context_engine = FakeContextEngine(context_by_tag or {})
    fleet_service = FakeFleetExecutiveSummaryService(fleet_summary or _fleet_summary())
    gateway = LTSAMessagingGateway(
        ltsa_knowledge_service=knowledge_service,
        engineering_context_engine=context_engine,
        fleet_executive_summary_service=fleet_service,
    )
    return gateway, knowledge_service, context_engine, fleet_service


# -- get_pump_summary(tag) -------------------------------------------------


def test_get_pump_summary_returns_a_message_response():
    gateway, _, _, _ = _gateway(
        knowledge_by_tag={"P-1": _knowledge("P-1")},
        context_by_tag={"P-1": _summary()},
    )

    response = gateway.get_pump_summary("P-1")

    assert isinstance(response, MessageResponse)
    assert response.success is True


def test_get_pump_summary_calls_knowledge_service_and_context_engine_exactly_once_each_one_aggregate():
    gateway, knowledge_service, context_engine, _ = _gateway(
        knowledge_by_tag={"P-1": _knowledge("P-1")},
        context_by_tag={"P-1": _summary()},
    )

    gateway.get_pump_summary("P-1")

    assert knowledge_service.calls == ["P-1"]
    assert context_engine.calls == ["P-1"]


def test_get_pump_summary_includes_engineering_insight_derived_from_the_top_recommendation_no_duplicate_calculation():
    gateway, _, _, _ = _gateway(
        knowledge_by_tag={"P-1": _knowledge("P-1", recommendation=(_recommendation(),))},
        context_by_tag={"P-1": _summary()},
    )

    response = gateway.get_pump_summary("P-1")

    assert response.data["insight"]["root_cause"] == (
        "An open Corrective Maintenance report with critical or major severity was found."
    )
    assert response.data["insight"]["recommended_action"] == "Dispatch a technician for immediate inspection."
    assert response.data["insight"]["risk"] == "CRITICAL"


def test_get_pump_summary_insight_is_none_when_no_recommendations_never_fabricated():
    gateway, _, _, _ = _gateway(
        knowledge_by_tag={"P-1": _knowledge("P-1", recommendation=())},
        context_by_tag={"P-1": _summary()},
    )

    response = gateway.get_pump_summary("P-1")

    assert response.data["insight"] is None


def test_get_pump_summary_includes_the_requested_tag_number():
    gateway, _, _, _ = _gateway(
        knowledge_by_tag={"P-1": _knowledge("P-1")},
        context_by_tag={"P-1": _summary()},
    )

    response = gateway.get_pump_summary("P-1")

    assert response.data["tag_number"] == "P-1"


# -- get_fleet_summary() --------------------------------------------------


def test_get_fleet_summary_returns_a_message_response():
    gateway, _, _, _ = _gateway()

    response = gateway.get_fleet_summary()

    assert isinstance(response, MessageResponse)
    assert response.success is True


def test_get_fleet_summary_calls_fleet_executive_summary_service_exactly_once_one_aggregate():
    gateway, _, _, fleet_service = _gateway()

    gateway.get_fleet_summary()

    assert fleet_service.calls == 1


def test_get_fleet_summary_includes_fleet_executive_summary_fields_unchanged_no_duplicate_calculation():
    gateway, _, _, _ = _gateway(fleet_summary=_fleet_summary(overall_health=72.0, fleet_status="NORMAL"))

    response = gateway.get_fleet_summary()

    assert response.data["summary"]["overall_health"] == 72.0
    assert response.data["summary"]["fleet_status"] == "NORMAL"


def test_get_fleet_summary_includes_fleet_insight_derived_from_the_same_summary():
    gateway, _, _, _ = _gateway(
        fleet_summary=_fleet_summary(top_risks=(_top_risk(priority=100, action="Dispatch now."),))
    )

    response = gateway.get_fleet_summary()

    assert response.data["insight"]["priority"] == 100
    assert response.data["insight"]["action"] == "Dispatch now."


def test_get_fleet_summary_insight_is_none_when_no_top_risks_never_fabricated():
    gateway, _, _, _ = _gateway(fleet_summary=_fleet_summary(top_risks=()))

    response = gateway.get_fleet_summary()

    assert response.data["insight"] is None


# -- MessageRequest / MessageResponse shape --------------------------------


def test_message_request_is_channel_agnostic_immutable_and_carries_intent_and_optional_tag():
    request = MessageRequest(intent="pump_summary", tag="P-1")

    assert request.intent == "pump_summary"
    assert request.tag == "P-1"

    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        request.intent = "tampered"


def test_message_request_tag_defaults_to_none_for_fleet_scoped_requests():
    request = MessageRequest(intent="fleet_summary")

    assert request.tag is None


def test_message_response_is_immutable():
    import pytest

    response = MessageResponse(success=True, data={})

    with pytest.raises(dataclasses.FrozenInstanceError):
        response.success = False


# -- structural guards ------------------------------------------------------


def _source() -> str:
    import sys
    from pathlib import Path

    core_services = Path(__file__).resolve().parents[2]
    if str(core_services) not in sys.path:
        sys.path.insert(0, str(core_services))
    return Path(__file__).resolve().parents[1].joinpath("ltsa_messaging_gateway.py").read_text(encoding="utf-8")


def _code_only(source: str) -> str:
    # Own explanatory comments/docstrings legitimately name the forbidden
    # terms while explaining they are NOT used -- strip everything that is
    # not executable code before checking, the same discipline
    # test_engineering_insight.py's own self-audit test already applies.
    import ast

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body[0] = ast.Pass()
    return ast.unparse(ast.fix_missing_locations(tree))


def test_no_sql_import():
    source = _source()
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for forbidden in ("sqlite3", "psycopg", "sqlalchemy"):
        assert not any(forbidden in line for line in import_lines)


def test_no_http_client_import():
    source = _source()
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for forbidden in ("requests", "httpx", "urllib.request", "aiohttp"):
        assert not any(forbidden in line for line in import_lines)


def test_no_whatsapp_sdk_import():
    code_only = _code_only(_source())
    lowered = code_only.lower()
    for forbidden in ("whatsapp", "twilio", "meta_business", "cloud_api"):
        assert forbidden not in lowered


def test_no_fastapi_or_router_import_no_ui_no_api():
    source = _source()
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for forbidden in ("fastapi", "APIRouter", "react", "jsx"):
        assert not any(forbidden in line for line in import_lines)


def test_module_reuses_ltsa_knowledge_service_and_engineering_context_engine_not_new_gateways():
    source = _source()
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    assert any("LTSAKnowledgeService" in line for line in import_lines)
    assert any("EngineeringContextEngine" in line for line in import_lines)
    assert any("FleetExecutiveSummaryService" in line for line in import_lines)
    assert any("build_engineering_insight" in line for line in import_lines)
    assert any("build_fleet_insight" in line for line in import_lines)
    forbidden_new_gateways = [
        "CMReportGateway", "WorkOrderGateway", "SealGateway", "SealStockGateway",
        "PumpGateway", "MaintenanceHistoryGateway",
    ]
    for forbidden in forbidden_new_gateways:
        assert not any(forbidden in line for line in import_lines)


def test_module_does_not_redefine_any_reused_class_or_function():
    source = _source()
    assert "class LTSAKnowledgeService" not in source
    assert "class EngineeringContextEngine" not in source
    assert "class FleetExecutiveSummaryService" not in source
    assert "def build_engineering_insight" not in source
    assert "def build_fleet_insight" not in source
    assert "class RecommendationEngine" not in source
