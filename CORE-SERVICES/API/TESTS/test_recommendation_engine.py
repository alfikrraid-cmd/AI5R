import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

import dataclasses

import pytest

from API.ltsa_knowledge_service import LTSAKnowledge
from API.recommendation_engine import Evidence, Recommendation, RecommendationEngine

TAG = "641-P-5"


def _knowledge(
    pump=None,
    seal=None,
    inventory=None,
    pm_history=None,
    cm_history=None,
    breakdown_history=None,
):
    return LTSAKnowledge(
        tag_number=TAG,
        pump=pump if pump is not None else {"tag_number": TAG},
        seal=seal or [],
        inventory=inventory or [],
        pm_history=pm_history if pm_history is not None else [{"pm_occurrence_code": "PM-OCC-001"}],
        cm_history=cm_history or [],
        breakdown_history=breakdown_history or [],
        drawings=None,
        recommendation=None,
        pm_schedules=[],
        condition_monitoring_schedules=[],
        condition_monitoring_readings=[],
    )


# -- Evidence value object ----------------------------------------------------


def test_evidence_is_immutable():
    evidence = Evidence(source="CMReport", reference="CM-1", field="severity", value="CRITICAL")

    with pytest.raises(dataclasses.FrozenInstanceError):
        evidence.value = "changed"


def test_evidence_is_hashable_and_equal_by_value():
    a = Evidence(source="CMReport", reference="CM-1", field="severity", value="CRITICAL")
    b = Evidence(source="CMReport", reference="CM-1", field="severity", value="CRITICAL")

    assert a == b
    assert hash(a) == hash(b)


# -- Recommendation value object -----------------------------------------------


def test_recommendation_is_immutable():
    rec = Recommendation(
        id="REC_PM_OVERDUE:641-P-5", rule_code="REC_PM_OVERDUE", priority=70, category="MAINTENANCE",
        title="t", description="d", evidence=(), confidence=1.0, action="a",
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        rec.priority = 10


def test_recommendation_is_hashable_and_equal_by_value():
    evidence = (Evidence(source="CMReport", reference="CM-1", field="severity", value="CRITICAL"),)
    a = Recommendation(id="REC_CRITICAL_CM:641-P-5", rule_code="REC_CRITICAL_CM", priority=100, category="INSPECTION", title="t", description="d", evidence=evidence, confidence=1.0, action="a")
    b = Recommendation(id="REC_CRITICAL_CM:641-P-5", rule_code="REC_CRITICAL_CM", priority=100, category="INSPECTION", title="t", description="d", evidence=evidence, confidence=1.0, action="a")

    assert a == b
    assert hash(a) == hash(b)


def test_recommendation_rejects_a_category_outside_the_allowed_set():
    with pytest.raises(ValueError):
        Recommendation(
            id="X:Y", rule_code="X", priority=50, category="NOT_ALLOWED",
            title="t", description="d", evidence=(), confidence=1.0, action="a",
        )


@pytest.mark.parametrize("category", ["MAINTENANCE", "RELIABILITY", "SPARE_PART", "INSPECTION"])
def test_recommendation_accepts_every_allowed_category(category):
    rec = Recommendation(
        id="X:Y", rule_code="X", priority=50, category=category,
        title="t", description="d", evidence=(), confidence=1.0, action="a",
    )

    assert rec.category == category


# -- PM overdue -------------------------------------------------------------


def test_pm_overdue_fires_when_no_pm_history_exists():
    engine = RecommendationEngine()
    knowledge = _knowledge(pm_history=[])

    recommendations = engine.recommend(knowledge)

    assert "Schedule PM" in [r.title for r in recommendations]


def test_pm_overdue_does_not_fire_when_pm_history_exists():
    engine = RecommendationEngine()
    knowledge = _knowledge(pm_history=[{"pm_occurrence_code": "PM-OCC-001"}])

    recommendations = engine.recommend(knowledge)

    assert "Schedule PM" not in [r.title for r in recommendations]


def test_pm_overdue_recommendation_fields():
    engine = RecommendationEngine()
    knowledge = _knowledge(pm_history=[])

    rec = next(r for r in engine.recommend(knowledge) if r.title == "Schedule PM")

    assert rec.rule_code == "REC_PM_OVERDUE"
    assert rec.id == f"REC_PM_OVERDUE:{TAG}"
    assert rec.category == "MAINTENANCE"
    assert rec.priority == 70
    assert rec.evidence == ()
    assert 0.0 < rec.confidence < 1.0  # disclosed approximation, not a hard fact


# -- Critical CM --------------------------------------------------------------


def test_critical_cm_fires_for_open_critical_report():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        cm_history=[{"cm_report_code": "CM-101", "severity": "CRITICAL", "status": "OPEN", "failure_category": "MECHANICAL"}]
    )

    recommendations = engine.recommend(knowledge)

    assert "Immediate Inspection" in [r.title for r in recommendations]


def test_critical_cm_fires_for_in_progress_major_report():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        cm_history=[{"cm_report_code": "CM-102", "severity": "MAJOR", "status": "IN_PROGRESS", "failure_category": "MECHANICAL"}]
    )

    recommendations = engine.recommend(knowledge)

    assert "Immediate Inspection" in [r.title for r in recommendations]


def test_critical_cm_does_not_fire_for_closed_report():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        cm_history=[{"cm_report_code": "CM-103", "severity": "CRITICAL", "status": "CLOSED", "failure_category": "MECHANICAL"}]
    )

    recommendations = engine.recommend(knowledge)

    assert "Immediate Inspection" not in [r.title for r in recommendations]


def test_critical_cm_does_not_fire_for_minor_severity():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        cm_history=[{"cm_report_code": "CM-104", "severity": "MINOR", "status": "OPEN", "failure_category": "MECHANICAL"}]
    )

    recommendations = engine.recommend(knowledge)

    assert "Immediate Inspection" not in [r.title for r in recommendations]


def test_critical_cm_recommendation_fields():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        cm_history=[
            {"cm_report_code": "CM-101", "severity": "CRITICAL", "status": "OPEN", "failure_category": "MECHANICAL"},
            {"cm_report_code": "CM-102", "severity": "MINOR", "status": "OPEN", "failure_category": "MECHANICAL"},
        ]
    )

    rec = next(r for r in engine.recommend(knowledge) if r.title == "Immediate Inspection")

    assert rec.rule_code == "REC_CRITICAL_CM"
    assert rec.id == f"REC_CRITICAL_CM:{TAG}"
    assert rec.category == "INSPECTION"
    assert rec.priority == 100
    assert rec.confidence == 1.0
    assert rec.evidence == (Evidence(source="CMReport", reference="CM-101", field="severity", value="CRITICAL"),)


# -- Repeated breakdown ---------------------------------------------------------


def test_repeated_breakdown_fires_at_two_or_more_breakdowns():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        breakdown_history=[{"maintenance_record_code": "MH-1"}, {"maintenance_record_code": "MH-2"}]
    )

    recommendations = engine.recommend(knowledge)

    assert "Root Cause Analysis" in [r.title for r in recommendations]


def test_repeated_breakdown_does_not_fire_for_a_single_breakdown():
    engine = RecommendationEngine()
    knowledge = _knowledge(breakdown_history=[{"maintenance_record_code": "MH-1"}])

    recommendations = engine.recommend(knowledge)

    assert "Root Cause Analysis" not in [r.title for r in recommendations]


def test_repeated_breakdown_threshold_is_dependency_injected():
    engine = RecommendationEngine(repeated_breakdown_threshold=3)
    knowledge = _knowledge(
        breakdown_history=[{"maintenance_record_code": "MH-1"}, {"maintenance_record_code": "MH-2"}]
    )

    recommendations = engine.recommend(knowledge)

    assert "Root Cause Analysis" not in [r.title for r in recommendations]


def test_repeated_breakdown_recommendation_fields():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        breakdown_history=[{"maintenance_record_code": "MH-1"}, {"maintenance_record_code": "MH-2"}]
    )

    rec = next(r for r in engine.recommend(knowledge) if r.title == "Root Cause Analysis")

    assert rec.rule_code == "REC_REPEATED_BREAKDOWN"
    assert rec.id == f"REC_REPEATED_BREAKDOWN:{TAG}"
    assert rec.category == "RELIABILITY"
    assert rec.priority == 90
    assert rec.evidence == (
        Evidence(source="MaintenanceHistory", reference="MH-1", field="maintenance_record_code", value="MH-1"),
        Evidence(source="MaintenanceHistory", reference="MH-2", field="maintenance_record_code", value="MH-2"),
    )


# -- Zero inventory ----------------------------------------------------------


def test_zero_inventory_fires_when_quantity_is_zero():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        inventory=[{"seal_code": "SC-001", "quantity_on_hand": 0, "reorder_point": 2, "location": "A"}]
    )

    recommendations = engine.recommend(knowledge)

    assert "Procurement Required" in [r.title for r in recommendations]


def test_zero_inventory_fires_when_quantity_is_unknown():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        inventory=[{"seal_code": "SC-009", "quantity_on_hand": None, "reorder_point": None, "location": None}]
    )

    recommendations = engine.recommend(knowledge)

    assert "Procurement Required" in [r.title for r in recommendations]


def test_zero_inventory_does_not_fire_when_stock_is_available():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        inventory=[{"seal_code": "SC-001", "quantity_on_hand": 4, "reorder_point": 2, "location": "A"}]
    )

    recommendations = engine.recommend(knowledge)

    assert "Procurement Required" not in [r.title for r in recommendations]


def test_zero_inventory_accepts_numeric_strings_from_live_stock_payloads():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        inventory=[{"seal_code": "SC-001", "quantity_on_hand": "0", "reorder_point": 2, "location": "A"}]
    )

    recommendations = engine.recommend(knowledge)

    assert "Procurement Required" in [r.title for r in recommendations]


def test_zero_inventory_recommendation_fields():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        inventory=[
            {"seal_code": "SC-001", "quantity_on_hand": 0, "reorder_point": 2, "location": "A"},
            {"seal_code": "SC-002", "quantity_on_hand": 5, "reorder_point": 2, "location": "A"},
        ]
    )

    rec = next(r for r in engine.recommend(knowledge) if r.title == "Procurement Required")

    assert rec.rule_code == "REC_NO_STOCK"
    assert rec.id == f"REC_NO_STOCK:{TAG}"
    assert rec.category == "SPARE_PART"
    assert rec.priority == 90
    assert rec.evidence == (Evidence(source="SealStock", reference="SC-001", field="quantity_on_hand", value="0"),)


# -- Mechanical seal leakage -------------------------------------------------------


def test_seal_leakage_fires_for_seal_failure_category():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        cm_history=[{"cm_report_code": "CM-201", "failure_category": "SEAL_FAILURE", "severity": "MODERATE", "status": "OPEN"}]
    )

    recommendations = engine.recommend(knowledge)

    assert "Inspect Mechanical Seal" in [r.title for r in recommendations]


def test_seal_leakage_does_not_fire_for_other_failure_categories():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        cm_history=[{"cm_report_code": "CM-202", "failure_category": "ELECTRICAL", "severity": "MODERATE", "status": "OPEN"}]
    )

    recommendations = engine.recommend(knowledge)

    assert "Inspect Mechanical Seal" not in [r.title for r in recommendations]


def test_seal_leakage_recommendation_fields():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        cm_history=[{"cm_report_code": "CM-201", "failure_category": "SEAL_FAILURE", "severity": "MODERATE", "status": "CLOSED"}]
    )

    rec = next(r for r in engine.recommend(knowledge) if r.title == "Inspect Mechanical Seal")

    assert rec.rule_code == "REC_SEAL_FAILURE"
    assert rec.id == f"REC_SEAL_FAILURE:{TAG}"
    assert rec.category == "INSPECTION"
    assert rec.priority == 90
    assert rec.evidence == (Evidence(source="CMReport", reference="CM-201", field="failure_category", value="SEAL_FAILURE"),)


# -- combinations / sorting / determinism / isolation --------------------------


def test_no_recommendations_when_no_rule_matches():
    engine = RecommendationEngine()
    knowledge = _knowledge(pm_history=[{"pm_occurrence_code": "PM-1"}])

    recommendations = engine.recommend(knowledge)

    assert recommendations == ()


def test_multiple_rules_fire_together_sorted_by_priority_descending():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        pm_history=[],
        cm_history=[{"cm_report_code": "CM-1", "severity": "CRITICAL", "status": "OPEN", "failure_category": "MECHANICAL"}],
        breakdown_history=[{"maintenance_record_code": "MH-1"}, {"maintenance_record_code": "MH-2"}],
        inventory=[{"seal_code": "SC-1", "quantity_on_hand": 0, "reorder_point": 1, "location": "A"}],
    )

    recommendations = engine.recommend(knowledge)
    priorities = [r.priority for r in recommendations]

    assert priorities == sorted(priorities, reverse=True)
    # Critical CM (100) must sort before the priority-90 tier, and
    # PM overdue (70) must sort last.
    assert recommendations[0].title == "Immediate Inspection"
    assert recommendations[-1].title == "Schedule PM"


def test_equal_priority_ties_break_by_stable_rule_evaluation_order():
    engine = RecommendationEngine()
    knowledge = _knowledge(
        pm_history=[{"pm_occurrence_code": "PM-1"}],
        breakdown_history=[{"maintenance_record_code": "MH-1"}, {"maintenance_record_code": "MH-2"}],
        inventory=[{"seal_code": "SC-1", "quantity_on_hand": 0, "reorder_point": 1, "location": "A"}],
        cm_history=[{"cm_report_code": "CM-1", "failure_category": "SEAL_FAILURE", "severity": "MODERATE", "status": "OPEN"}],
    )

    titles = [r.title for r in engine.recommend(knowledge)]

    # All three are priority 90; evaluation order is Breakdown, Inventory, Seal.
    assert titles == ["Root Cause Analysis", "Procurement Required", "Inspect Mechanical Seal"]


def test_output_is_a_tuple():
    engine = RecommendationEngine()
    knowledge = _knowledge(pm_history=[])

    result = engine.recommend(knowledge)

    assert isinstance(result, tuple)


def test_recommend_is_deterministic_across_repeated_calls():
    engine = RecommendationEngine()
    knowledge = _knowledge(pm_history=[])

    first = engine.recommend(knowledge)
    second = engine.recommend(knowledge)

    assert first == second


def test_id_contains_no_uuid_or_random_component():
    engine = RecommendationEngine()
    knowledge = _knowledge(pm_history=[])

    first = engine.recommend(knowledge)[0].id
    second = engine.recommend(knowledge)[0].id

    assert first == second == f"REC_PM_OVERDUE:{TAG}"


# -- isolation: rules are independently testable -------------------------------


def test_pm_overdue_rule_is_independently_callable():
    engine = RecommendationEngine()
    knowledge = _knowledge(pm_history=[])

    result = engine._check_pm_overdue(knowledge)

    assert result is not None
    assert result.title == "Schedule PM"


def test_critical_cm_rule_is_independently_callable():
    engine = RecommendationEngine()
    knowledge = _knowledge(cm_history=[])

    result = engine._check_critical_cm(knowledge)

    assert result is None


# -- PM overdue heuristic: unchanged runtime behavior, disclosed comment --------


def test_pm_overdue_heuristic_comment_is_present_and_behavior_is_unchanged():
    source = Path(__file__).resolve().parents[1].joinpath("recommendation_engine.py").read_text(encoding="utf-8")

    assert "Temporary heuristic" in source
    assert "PM Schedule" in source

    # Behavior proof, not just a comment: still fires purely on empty
    # pm_history, still confidence 0.6 -- nothing else changed.
    engine = RecommendationEngine()
    rec = engine._check_pm_overdue(_knowledge(pm_history=[]))
    assert rec.confidence == 0.6
    assert engine._check_pm_overdue(_knowledge(pm_history=[{"pm_occurrence_code": "PM-1"}])) is None


# -- no LLM / no AI reasoning, structural verification --------------------------


def test_module_contains_no_llm_or_ai_client_dependency():
    source = Path(__file__).resolve().parents[1].joinpath("recommendation_engine.py").read_text(encoding="utf-8")
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for forbidden in ("EngineeringAIClient", "postEngineeringAI", "AI_RUNTIME", "EngineeringPromptBuilder", "openai", "anthropic"):
        assert not any(forbidden in line for line in import_lines)


def test_module_reuses_ltsa_knowledge_type_not_a_redefinition():
    source = Path(__file__).resolve().parents[1].joinpath("recommendation_engine.py").read_text(encoding="utf-8")
    assert "from .ltsa_knowledge_service import" in source or "from API.ltsa_knowledge_service import" in source
    assert "class LTSAKnowledge" not in source


def test_module_makes_no_gateway_or_sql_calls():
    source = Path(__file__).resolve().parents[1].joinpath("recommendation_engine.py").read_text(encoding="utf-8")
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for forbidden in ("Gateway", "sqlite3", "fastapi", "APIRouter"):
        assert not any(forbidden in line for line in import_lines)
