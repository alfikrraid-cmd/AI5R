from API.fleet_executive_summary import FleetExecutiveSummary, FleetExecutiveSummaryService, TopRisk
from API.fleet_reliability_service import FleetReliability
from API.ltsa_knowledge_service import LTSAKnowledge
from API.recommendation_engine import Recommendation

# MWO-LTSA-037E -- FleetExecutiveSummaryService: deterministic executive
# rollup reusing only FleetReliabilityService (fleet-wide totals),
# ExecutiveMetrics (indirectly, via FleetReliability -- computed once,
# inside FleetReliabilityService, never a second time here), and
# RecommendationEngine's output (knowledge.recommendation, already
# populated by LTSAKnowledgeService.build() -- RecommendationEngine is
# never invoked a second time here either). No LLM, no prompt, no new
# gateway, no new pump-discovery logic -- per-pump detail comes from
# FleetReliabilityService.list_pump_knowledge() (MWO-LTSA-037E's own
# minimal, additive extension to that service), not from a second,
# independent pump iteration.


class FakeFleetReliabilityService:
    def __init__(self, reliability, knowledge):
        self._reliability = reliability
        self._knowledge = knowledge
        self.build_calls = 0
        self.list_pump_knowledge_calls = 0
        self.aggregate_from_knowledge_calls = 0
        # MWO-LTSA-FLEET-ATTENTION-001 -- a minimal stand-in for
        # LTSAKnowledgeService.recommendation_engine, which
        # FleetExecutiveSummaryService now reaches for (via
        # fleet_reliability_service.ltsa_knowledge_service.
        # recommendation_engine) to recompute fleet-aware recommendations
        # from already-fetched knowledge -- see RecommendationEngine's own
        # real implementation; this fake just returns knowledge.recommendation
        # unchanged so every pre-existing test's injected recommendation
        # tuple keeps flowing through top_risks/critical_asset_count exactly
        # as before.
        self.ltsa_knowledge_service = _FakeKnowledgeServiceHolder()

    def build(self, *, scope=None):
        self.build_calls += 1
        return self._reliability

    def list_pump_knowledge(self, *, scope=None):
        self.list_pump_knowledge_calls += 1
        return self._knowledge

    def list_pump_knowledge_fast(self, *, scope=None):
        # MWO-LTSA-FLEET-ANALYTICS-001 -- FleetExecutiveSummaryService.
        # build() now calls list_pump_knowledge_fast() (the real
        # FleetReliabilityService's own batch-or-fallback method); this
        # fake mirrors that same public interface, delegating to the
        # existing list_pump_knowledge_calls counter so every pre-existing
        # assertion on it keeps working unchanged.
        return self.list_pump_knowledge(scope=scope)

    def aggregate_from_knowledge(self, knowledge):
        self.aggregate_from_knowledge_calls += 1
        return self._reliability


class _FakeRecommendationEngine:
    def recommend(self, knowledge, summary=None):
        return knowledge.recommendation


class _FakeKnowledgeServiceHolder:
    def __init__(self):
        self.recommendation_engine = _FakeRecommendationEngine()


def _reliability(**overrides):
    defaults = dict(
        pump_count=2,
        fleet_health_score=85.0,
        fleet_mtbf_days=20.0,
        fleet_mttr_hours=4.0,
        fleet_availability=99.17,
        total_breakdown_count=1,
        total_critical_spare_count=0,
    )
    defaults.update(overrides)
    return FleetReliability(**defaults)


def _recommendation(tag, priority, rule_code="REC_CRITICAL_CM", title="Immediate Inspection", action="Inspect"):
    return Recommendation(
        id=f"{rule_code}:{tag}",
        rule_code=rule_code,
        priority=priority,
        category="INSPECTION",
        title=title,
        description="test",
        evidence=(),
        confidence=1.0,
        action=action,
    )


def _knowledge(tag, recommendation=()):
    return LTSAKnowledge(
        tag_number=tag,
        pump={"tag_number": tag},
        seal=[],
        inventory=[],
        pm_history=[],
        cm_history=[],
        breakdown_history=[],
        drawings=[],
        recommendation=recommendation,
        pm_schedules=[],
        condition_monitoring_schedules=[],
        condition_monitoring_readings=[],
    )


def _service(reliability, knowledge):
    fake = FakeFleetReliabilityService(reliability, knowledge)
    return FleetExecutiveSummaryService(fleet_reliability_service=fake), fake


# -- reuse: FleetReliability fields pass through unchanged -------------------


def test_overall_health_is_fleet_health_score_from_fleet_reliability_service():
    service, _ = _service(_reliability(fleet_health_score=72.5), (_knowledge("P-1"),))

    summary = service.build()

    assert summary.overall_health == 72.5


def test_fleet_availability_breakdown_and_critical_spare_pass_through_unchanged_no_duplicate_calculation():
    service, _ = _service(
        _reliability(fleet_availability=91.3, total_breakdown_count=7, total_critical_spare_count=3),
        (),
    )

    summary = service.build()

    assert summary.fleet_availability == 91.3
    assert summary.breakdown_count == 7
    assert summary.critical_spare_count == 3


def test_calls_fleet_reliability_service_build_exactly_once_no_backend_duplication():
    # MWO-LTSA-FLEET-ATTENTION-001 -- build() is no longer called at all
    # (FleetReliabilityService.build() itself used to independently re-fetch
    # every pump's knowledge a second time, the dominant cause of this
    # query's own reported latency). Reliability is now derived from the
    # SAME already-fetched knowledge via aggregate_from_knowledge() (pure,
    # no I/O) -- strictly LESS backend duplication than the property this
    # test's own name already asserted, not a regression of it.
    service, fake = _service(_reliability(), (_knowledge("P-1"),))

    service.build()

    assert fake.build_calls == 0
    assert fake.aggregate_from_knowledge_calls == 1


# MWO-LTSA-038B -- fleet_mtbf_days / fleet_mttr_hours added: pure
# pass-through from FleetReliability (037B), which already computes them;
# no new calculation, no new gateway, no second FleetReliabilityService
# call (still exactly the one .build() call from
# test_calls_fleet_reliability_service_build_exactly_once_no_backend_duplication
# above).


def test_fleet_mtbf_and_mttr_pass_through_unchanged_no_duplicate_calculation():
    service, _ = _service(_reliability(fleet_mtbf_days=42.3, fleet_mttr_hours=6.25), ())

    summary = service.build()

    assert summary.fleet_mtbf_days == 42.3
    assert summary.fleet_mttr_hours == 6.25


def test_fleet_mtbf_and_mttr_are_none_when_fleet_reliability_has_no_data_never_fabricated():
    service, _ = _service(_reliability(fleet_mtbf_days=None, fleet_mttr_hours=None), ())

    summary = service.build()

    assert summary.fleet_mtbf_days is None
    assert summary.fleet_mttr_hours is None


def test_calls_list_pump_knowledge_exactly_once():
    service, fake = _service(_reliability(), (_knowledge("P-1"),))

    service.build()

    assert fake.list_pump_knowledge_calls == 1


# -- fleet_status --------------------------------------------------------


def test_fleet_status_is_normal_when_health_score_is_high():
    service, _ = _service(_reliability(fleet_health_score=95.0), ())

    summary = service.build()

    assert summary.fleet_status == "NORMAL"


def test_fleet_status_is_attention_for_a_mid_range_health_score():
    service, _ = _service(_reliability(fleet_health_score=60.0), ())

    summary = service.build()

    assert summary.fleet_status == "ATTENTION"


def test_fleet_status_is_critical_for_a_low_health_score():
    service, _ = _service(_reliability(fleet_health_score=30.0), ())

    summary = service.build()

    assert summary.fleet_status == "CRITICAL"


def test_fleet_status_is_unknown_when_no_health_score_exists_never_fabricated():
    service, _ = _service(_reliability(fleet_health_score=None), ())

    summary = service.build()

    assert summary.fleet_status == "UNKNOWN"


# -- critical_asset_count -------------------------------------------------


def test_critical_asset_count_counts_pumps_with_a_priority_critical_recommendation():
    knowledge = (
        _knowledge("P-1", recommendation=(_recommendation("P-1", priority=100),)),
        _knowledge("P-2", recommendation=(_recommendation("P-2", priority=90),)),
        _knowledge("P-3", recommendation=()),
    )
    service, _ = _service(_reliability(), knowledge)

    summary = service.build()

    assert summary.critical_asset_count == 1


def test_critical_asset_count_is_zero_when_no_pump_has_a_critical_recommendation():
    knowledge = (_knowledge("P-1", recommendation=(_recommendation("P-1", priority=70),)),)
    service, _ = _service(_reliability(), knowledge)

    summary = service.build()

    assert summary.critical_asset_count == 0


def test_critical_asset_count_reuses_recommendation_engines_priority_critical_constant():
    from API.recommendation_engine import PRIORITY_CRITICAL

    assert PRIORITY_CRITICAL == 100
    source = __import__("pathlib").Path(
        __file__
    ).resolve().parents[1].joinpath("fleet_executive_summary.py").read_text(encoding="utf-8")
    assert "PRIORITY_CRITICAL" in source


# -- top_risks -------------------------------------------------------------


def test_top_risks_are_sorted_by_priority_descending():
    knowledge = (
        _knowledge("P-1", recommendation=(_recommendation("P-1", priority=70, rule_code="REC_PM_OVERDUE"),)),
        _knowledge("P-2", recommendation=(_recommendation("P-2", priority=100, rule_code="REC_CRITICAL_CM"),)),
        _knowledge("P-3", recommendation=(_recommendation("P-3", priority=90, rule_code="REC_NO_STOCK"),)),
    )
    service, _ = _service(_reliability(), knowledge)

    summary = service.build()

    assert [risk.priority for risk in summary.top_risks] == [100, 90, 70]
    assert summary.top_risks[0].tag_number == "P-2"
    assert summary.top_risks[0].rule_code == "REC_CRITICAL_CM"


def test_top_risks_are_capped_at_five():
    knowledge = tuple(
        _knowledge(f"P-{i}", recommendation=(_recommendation(f"P-{i}", priority=70 + i),))
        for i in range(8)
    )
    service, _ = _service(_reliability(), knowledge)

    summary = service.build()

    assert len(summary.top_risks) == 5


def test_top_risks_is_empty_when_no_pump_has_a_recommendation():
    service, _ = _service(_reliability(), (_knowledge("P-1"),))

    summary = service.build()

    assert summary.top_risks == ()


def test_top_risk_fields_carry_tag_rule_code_title_priority_action_and_description():
    knowledge = (
        _knowledge(
            "P-1",
            recommendation=(
                _recommendation("P-1", priority=100, rule_code="REC_CRITICAL_CM", title="Immediate Inspection", action="Dispatch a technician."),
            ),
        ),
    )
    service, _ = _service(_reliability(), knowledge)

    summary = service.build()

    assert summary.top_risks[0] == TopRisk(
        tag_number="P-1",
        rule_code="REC_CRITICAL_CM",
        title="Immediate Inspection",
        priority=100,
        action="Dispatch a technician.",
        description="test",
    )


def test_top_risks_handles_a_none_recommendation_field_gracefully():
    knowledge = (_knowledge("P-1", recommendation=None),)
    service, _ = _service(_reliability(), knowledge)

    summary = service.build()

    assert summary.top_risks == ()


# -- overall shape / determinism ------------------------------------------


def test_returns_a_fleet_executive_summary_instance():
    service, _ = _service(_reliability(), (_knowledge("P-1"),))

    summary = service.build()

    assert isinstance(summary, FleetExecutiveSummary)


def test_is_deterministic_across_repeated_calls():
    knowledge = (
        _knowledge("P-1", recommendation=(_recommendation("P-1", priority=100),)),
        _knowledge("P-2", recommendation=(_recommendation("P-2", priority=90),)),
    )
    service, _ = _service(_reliability(), knowledge)

    first = service.build()
    second = service.build()

    assert first == second


# -- no LLM / no prompt / no new gateway / no duplicate aggregate --------


def test_module_makes_no_llm_prompt_gateway_or_api_call():
    source = __import__("pathlib").Path(
        __file__
    ).resolve().parents[1].joinpath("fleet_executive_summary.py").read_text(encoding="utf-8")
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for forbidden in (
        "Gateway", "sqlite3", "fastapi", "APIRouter", "EngineeringAIClient",
        "EngineeringPromptBuilder", "AI_RUNTIME", "openai", "anthropic",
    ):
        assert not any(forbidden in line for line in import_lines)


def test_module_reuses_fleet_reliability_service_not_a_redefinition():
    source = __import__("pathlib").Path(
        __file__
    ).resolve().parents[1].joinpath("fleet_executive_summary.py").read_text(encoding="utf-8")
    assert "from .fleet_reliability_service import" in source or "from API.fleet_reliability_service import" in source
    assert "class FleetReliability" not in source
    assert "def compute_executive_metrics" not in source
    assert "class RecommendationEngine" not in source
