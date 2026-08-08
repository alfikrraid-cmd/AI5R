import dataclasses
from pathlib import Path

import pytest

from API.fleet_executive_summary import FleetExecutiveSummary, TopRisk
from API.fleet_insight import FleetInsight, build_fleet_insight

# MWO-LTSA-037F -- FleetInsight: same composition style as
# EngineeringInsight (MWO-LTSA-035) -- pure field selection over an
# already-built FleetExecutiveSummary's own top_risks[0] (already sorted
# by priority descending, MWO-LTSA-037E). No re-ranking, no LLM, no
# prompt. Test conventions mirror test_engineering_insight.py directly.


def _top_risk(**overrides):
    defaults = dict(
        tag_number="641-P-5",
        rule_code="REC_CRITICAL_CM",
        title="Immediate Inspection",
        priority=100,
        action="Dispatch a technician for immediate inspection.",
        description="An open Corrective Maintenance report with critical or major severity was found.",
    )
    defaults.update(overrides)
    return TopRisk(**defaults)


def _summary(**overrides):
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


def test_returns_none_when_no_top_risks():
    insight = build_fleet_insight(_summary(top_risks=()))

    assert insight is None


def test_priority_is_top_risk_priority():
    insight = build_fleet_insight(_summary(top_risks=(_top_risk(priority=90),)))

    assert insight.priority == 90


def test_action_is_top_risk_action():
    insight = build_fleet_insight(_summary(top_risks=(_top_risk(action="Initiate procurement."),)))

    assert insight.action == "Initiate procurement."


def test_reason_is_top_risk_description():
    insight = build_fleet_insight(
        _summary(top_risks=(_top_risk(description="Repeated breakdown-linked maintenance records found."),))
    )

    assert insight.reason == "Repeated breakdown-linked maintenance records found."


def test_summary_mentions_fleet_status_critical_asset_count_and_top_risk():
    insight = build_fleet_insight(
        _summary(
            fleet_status="CRITICAL",
            critical_asset_count=3,
            top_risks=(_top_risk(tag_number="P-9", title="Immediate Inspection"),),
        )
    )

    assert "CRITICAL" in insight.summary
    assert "3" in insight.summary
    assert "P-9" in insight.summary
    assert "Immediate Inspection" in insight.summary


def test_uses_first_top_risk_without_resorting():
    # FleetExecutiveSummary.top_risks is already sorted by priority
    # descending -- build_fleet_insight must not re-derive or re-rank it,
    # it simply takes index 0, whatever order the caller passed in.
    high = _top_risk(tag_number="P-high", priority=100, action="high action", description="high desc")
    low = _top_risk(tag_number="P-low", priority=70, action="low action", description="low desc")

    insight = build_fleet_insight(_summary(top_risks=(high, low)))

    assert insight.priority == 100
    assert insight.action == "high action"
    assert insight.reason == "high desc"


def test_fleet_insight_is_immutable():
    insight = build_fleet_insight(_summary())

    with pytest.raises(dataclasses.FrozenInstanceError):
        insight.priority = 0


def _strip_comments_and_docstrings(source: str) -> str:
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
    stripped = ast.unparse(ast.fix_missing_locations(tree))
    return stripped


def test_no_forbidden_ai_terms_in_module_source():
    source = Path(__file__).resolve().parents[1].joinpath("fleet_insight.py").read_text(encoding="utf-8")
    code_only = _strip_comments_and_docstrings(source)
    forbidden = ["openai", "anthropic", "ollama", "claude", "requests.", "urllib.request", "httpx", "prompt"]
    lowered = code_only.lower()
    for term in forbidden:
        assert term not in lowered, f"forbidden term found in fleet_insight.py: {term}"


def test_module_makes_no_gateway_sql_or_router_call():
    source = Path(__file__).resolve().parents[1].joinpath("fleet_insight.py").read_text(encoding="utf-8")
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for forbidden in ("Gateway", "sqlite3", "fastapi", "APIRouter"):
        assert not any(forbidden in line for line in import_lines)


def test_module_does_not_redefine_recommendation_engine_or_fleet_executive_summary():
    source = Path(__file__).resolve().parents[1].joinpath("fleet_insight.py").read_text(encoding="utf-8")
    assert "class RecommendationEngine" not in source
    assert "class FleetExecutiveSummary" not in source
    assert "class TopRisk" not in source
