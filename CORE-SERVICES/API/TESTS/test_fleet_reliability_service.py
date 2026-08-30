# MWO-LTSA-037C -- these tests exercise the FleetReliabilityService that
# already landed under MWO-LTSA-037B, confirming its real, observed
# behavior (method name .build(), None-safe empty-fleet fields, the
# mtbf/mttr unit-converted availability formula) rather than re-designing
# it -- this MWO's own scope is exposing it via a router, not building it.

from pathlib import Path

from API.fleet_reliability_service import FleetReliability, FleetReliabilityService
from API.ltsa_knowledge_service import LTSAKnowledge
from API.recommendation_engine import Recommendation


class FakePumpGateway:
    def __init__(self, records):
        self._records = records
        self.calls = 0

    def list_pumps(self):
        self.calls += 1
        return {"success": True, "data": self._records}


class FakeKnowledgeService:
    def __init__(self, by_tag):
        self._by_tag = by_tag
        self.calls = []

    def build(self, tag_number):
        self.calls.append(tag_number)
        return self._by_tag[tag_number]


def _recommendation(tag, priority):
    return Recommendation(
        id=f"REC_CRITICAL_CM:{tag}",
        rule_code="REC_CRITICAL_CM",
        priority=priority,
        category="INSPECTION",
        title="Immediate Inspection",
        description="test",
        evidence=(),
        confidence=1.0,
        action="test",
    )


def _knowledge(tag, **overrides):
    defaults = dict(
        tag_number=tag,
        pump={"tag_number": tag},
        seal=[],
        inventory=[],
        pm_history=[],
        cm_history=[],
        breakdown_history=[],
        drawings=None,
        recommendation=(),
        pm_schedules=[],
        condition_monitoring_schedules=[],
        condition_monitoring_readings=[],
    )
    defaults.update(overrides)
    return LTSAKnowledge(**defaults)


def _service(tags, by_tag):
    pump_gateway = FakePumpGateway([{"tag_number": tag} for tag in tags])
    knowledge_service = FakeKnowledgeService(by_tag)
    service = FleetReliabilityService(pump_gateway=pump_gateway, ltsa_knowledge_service=knowledge_service)
    return service, pump_gateway, knowledge_service


def test_lists_pumps_via_pump_gateway():
    service, pump_gateway, _ = _service(["P-A"], {"P-A": _knowledge("P-A")})

    service.build()

    assert pump_gateway.calls == 1


def test_builds_knowledge_once_per_pump_via_ltsa_knowledge_service():
    service, _, knowledge_service = _service(
        ["P-A", "P-B"], {"P-A": _knowledge("P-A"), "P-B": _knowledge("P-B")}
    )

    service.build()

    assert knowledge_service.calls == ["P-A", "P-B"]


def test_pump_count_matches_number_of_pumps_listed():
    service, _, _ = _service(["P-A", "P-B"], {"P-A": _knowledge("P-A"), "P-B": _knowledge("P-B")})

    result = service.build()

    assert result.pump_count == 2


def test_empty_fleet_returns_all_none_and_zero_fields_never_fabricated():
    service, _, _ = _service([], {})

    result = service.build()

    assert result == FleetReliability(
        pump_count=0,
        fleet_health_score=None,
        fleet_mtbf_days=None,
        fleet_mttr_hours=None,
        fleet_availability=None,
        total_breakdown_count=0,
        total_critical_spare_count=0,
    )


def test_pump_records_without_a_tag_number_are_skipped():
    pump_gateway = FakePumpGateway([{"tag_number": "P-A"}, {"other_field": "no tag"}])
    knowledge_service = FakeKnowledgeService({"P-A": _knowledge("P-A")})
    service = FleetReliabilityService(pump_gateway=pump_gateway, ltsa_knowledge_service=knowledge_service)

    result = service.build()

    assert result.pump_count == 1
    assert knowledge_service.calls == ["P-A"]


def test_fleet_health_score_is_mean_of_per_pump_health_scores():
    by_tag = {
        "P-A": _knowledge("P-A", recommendation=()),
        "P-B": _knowledge("P-B", recommendation=(_recommendation("P-B", 90),)),
    }
    service, _, _ = _service(["P-A", "P-B"], by_tag)

    result = service.build()

    assert result.fleet_health_score == 55.0


def test_fleet_mtbf_and_mttr_are_mean_of_non_none_per_pump_values():
    by_tag = {
        "P-A": _knowledge(
            "P-A",
            cm_history=[
                {"created_at": "2026-01-01", "downtime_hours": 4},
                {"created_at": "2026-01-11", "downtime_hours": 6},
            ],
        ),
        "P-B": _knowledge(
            "P-B",
            cm_history=[
                {"created_at": "2026-02-01", "downtime_hours": 2},
                {"created_at": "2026-02-21", "downtime_hours": 8},
            ],
        ),
    }
    service, _, _ = _service(["P-A", "P-B"], by_tag)

    result = service.build()

    assert result.fleet_mtbf_days == 15.0
    assert result.fleet_mttr_hours == 5.0


def test_fleet_availability_converts_mttr_hours_to_days_before_combining_with_mtbf():
    by_tag = {
        "P-A": _knowledge(
            "P-A",
            cm_history=[
                {"created_at": "2026-01-01", "downtime_hours": 4},
                {"created_at": "2026-01-11", "downtime_hours": 6},
            ],
        ),
        "P-B": _knowledge(
            "P-B",
            cm_history=[
                {"created_at": "2026-02-01", "downtime_hours": 2},
                {"created_at": "2026-02-21", "downtime_hours": 8},
            ],
        ),
    }
    service, _, _ = _service(["P-A", "P-B"], by_tag)

    result = service.build()

    # mtbf_days=15.0, mttr_hours=5.0 -> mttr_days=5/24;
    # 15 / (15 + 5/24) * 100, rounded to 2 decimals.
    assert result.fleet_availability == 98.63


def test_fleet_availability_is_none_when_no_pump_has_mtbf_or_mttr_data():
    service, _, _ = _service(["P-A"], {"P-A": _knowledge("P-A")})

    result = service.build()

    assert result.fleet_mtbf_days is None
    assert result.fleet_mttr_hours is None
    assert result.fleet_availability is None


def test_total_breakdown_count_is_sum_across_fleet_no_duplicate_calculation():
    by_tag = {
        "P-A": _knowledge("P-A", breakdown_history=[{"maintenance_record_code": "MH-1"}]),
        "P-B": _knowledge(
            "P-B",
            breakdown_history=[
                {"maintenance_record_code": "MH-2"},
                {"maintenance_record_code": "MH-3"},
            ],
        ),
    }
    service, _, _ = _service(["P-A", "P-B"], by_tag)

    result = service.build()

    assert result.total_breakdown_count == 3


def test_total_critical_spare_count_is_sum_across_fleet():
    by_tag = {
        "P-A": _knowledge("P-A", inventory=[{"seal_code": "SC-1", "quantity_on_hand": 0}]),
        "P-B": _knowledge("P-B", inventory=[{"seal_code": "SC-2", "quantity_on_hand": None}]),
    }
    service, _, _ = _service(["P-A", "P-B"], by_tag)

    result = service.build()

    assert result.total_critical_spare_count == 2


# MWO-LTSA-037E -- list_pump_knowledge(): minimal, additive extension.
# FleetExecutiveSummaryService needs per-pump LTSAKnowledge (for Critical
# Assets and Top Risks, both inherently per-pump) but the mission's reuse
# list authorizes only FleetReliabilityService/ExecutiveMetrics/
# RecommendationEngine, not PumpGateway/LTSAKnowledgeService directly --
# so pump discovery + per-pump knowledge building is exposed here, reusing
# the exact same _list_pump_tags() this service's own .build() already
# uses, rather than re-implementing pump iteration a second time anywhere
# else. .build()/._aggregate() are untouched by this addition.


def test_list_pump_knowledge_returns_one_ltsa_knowledge_per_pump():
    by_tag = {"P-A": _knowledge("P-A"), "P-B": _knowledge("P-B")}
    service, _, knowledge_service = _service(["P-A", "P-B"], by_tag)

    result = service.list_pump_knowledge()

    assert result == (by_tag["P-A"], by_tag["P-B"])
    assert knowledge_service.calls == ["P-A", "P-B"]


def test_list_pump_knowledge_is_empty_for_an_empty_fleet():
    service, _, _ = _service([], {})

    result = service.list_pump_knowledge()

    assert result == ()


def test_list_pump_knowledge_skips_pump_records_without_a_tag_number():
    pump_gateway = FakePumpGateway([{"tag_number": "P-A"}, {"other_field": "no tag"}])
    knowledge_service = FakeKnowledgeService({"P-A": _knowledge("P-A")})
    service = FleetReliabilityService(pump_gateway=pump_gateway, ltsa_knowledge_service=knowledge_service)

    result = service.list_pump_knowledge()

    assert len(result) == 1
    assert result[0].tag_number == "P-A"


def test_list_pump_knowledge_reuses_list_pump_tags_no_duplicate_pump_discovery():
    source = Path(__file__).resolve().parents[1].joinpath("fleet_reliability_service.py").read_text(encoding="utf-8")
    assert source.count("def _list_pump_tags") == 1
    assert "def list_pump_knowledge" in source
    # list_pump_knowledge's own body must call _list_pump_tags, not
    # re-read pump_gateway.list_pumps() a second, independent way.
    body_start = source.index("def list_pump_knowledge")
    body = source[body_start : body_start + 700]
    assert "_list_pump_tags" in body


# -- MWO-LTSA-FLEET-ANALYTICS-001 readiness closure: document-gateway audit --


def test_recommendation_engine_never_reads_drawings_field():
    """Phase 4's own audit question: does any RecommendationEngine rule
    require document data in a way that would force list_pump_knowledge_
    from_batch()'s always-empty `drawings` field back to a per-pump
    fallback? Answer: no -- proven here by inspecting the real
    recommendation_engine.py source for any `knowledge.drawings` /
    `.drawings` reference, not assumed. If a future rule starts reading
    drawings, THIS test fails first, rather than silently reintroducing
    an N+1 document-gateway fallback inside list_pump_knowledge_from_batch."""
    source = (
        Path(__file__).resolve().parents[1].joinpath("recommendation_engine.py").read_text(encoding="utf-8")
    )
    assert "drawings" not in source


def test_recommendation_engine_field_reads_are_a_known_closed_set():
    """The complete set of LTSAKnowledge fields RecommendationEngine.
    recommend() reads, confirmed by source inspection -- documents
    exactly why list_pump_knowledge_from_batch() only needs to populate
    tag_number/condition_monitoring_readings/cm_history/breakdown_history/
    inventory correctly (drawings/condition_monitoring_schedules/
    work_orders can safely stay empty tuples)."""
    import re

    source = (
        Path(__file__).resolve().parents[1].joinpath("recommendation_engine.py").read_text(encoding="utf-8")
    )
    fields_read = set(re.findall(r"knowledge\.(\w+)", source))
    assert fields_read == {"tag_number", "condition_monitoring_readings", "cm_history", "breakdown_history", "inventory"}
