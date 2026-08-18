import sys
from datetime import date
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.executive_metrics import ExecutiveMetrics, compute_executive_metrics
from API.ltsa_knowledge_service import LTSAKnowledge
from API.recommendation_engine import Recommendation

TAG = "641-P-5"
TODAY = date(2026, 8, 7)


def _knowledge(
    cm_history=None,
    breakdown_history=None,
    pm_schedules=None,
    inventory=None,
    recommendation=(),
):
    return LTSAKnowledge(
        tag_number=TAG,
        pump={"tag_number": TAG},
        seal=[],
        inventory=inventory or [],
        pm_history=[],
        cm_history=cm_history or [],
        breakdown_history=breakdown_history or [],
        drawings=[],
        recommendation=recommendation,
        pm_schedules=pm_schedules or [],
        condition_monitoring_schedules=[],
        condition_monitoring_readings=[],
    )


def _recommendation(**overrides):
    defaults = dict(
        id="REC_CRITICAL_CM:641-P-5", rule_code="REC_CRITICAL_CM", priority=100, category="INSPECTION",
        title="Immediate Inspection", description="d", evidence=(), confidence=1.0, action="a",
    )
    defaults.update(overrides)
    return Recommendation(**defaults)


# -- health_score --------------------------------------------------------


def test_health_score_is_100_when_no_recommendations_exist():
    knowledge = _knowledge(recommendation=())

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.health_score == 100


def test_health_score_deducts_the_worst_priority_recommendation():
    knowledge = _knowledge(recommendation=(_recommendation(priority=90), _recommendation(priority=70)))

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.health_score == 10  # 100 - 90 (worst of the two)


def test_health_score_floors_at_zero_for_a_critical_recommendation():
    knowledge = _knowledge(recommendation=(_recommendation(priority=100),))

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.health_score == 0


def test_health_score_is_none_safe_when_recommendation_field_is_none():
    # LTSAKnowledge.recommendation is typed `Any` -- a directly-constructed
    # instance can legitimately pass None (several existing tests do).
    knowledge = _knowledge(recommendation=None)

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.health_score == 100


# -- mtbf_days -------------------------------------------------------------


def test_mtbf_is_none_with_fewer_than_two_cm_reports():
    knowledge = _knowledge(cm_history=[{"cm_report_code": "CM-1", "created_at": "2026-06-01T00:00:00Z"}])

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.mtbf_days is None


def test_mtbf_is_none_with_zero_cm_reports():
    knowledge = _knowledge(cm_history=[])

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.mtbf_days is None


def test_mtbf_averages_the_gap_between_consecutive_cm_reports():
    knowledge = _knowledge(
        cm_history=[
            {"cm_report_code": "CM-1", "created_at": "2026-06-01T00:00:00Z"},
            {"cm_report_code": "CM-2", "created_at": "2026-06-11T00:00:00Z"},
            {"cm_report_code": "CM-3", "created_at": "2026-07-01T00:00:00Z"},
        ]
    )

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    # Gaps: 10 days (Jun 1 -> Jun 11), 20 days (Jun 11 -> Jul 1) -> mean 15.
    assert metrics.mtbf_days == 15.0


def test_mtbf_is_order_independent_records_are_sorted_before_gaps_are_measured():
    knowledge = _knowledge(
        cm_history=[
            {"cm_report_code": "CM-2", "created_at": "2026-06-11T00:00:00Z"},
            {"cm_report_code": "CM-1", "created_at": "2026-06-01T00:00:00Z"},
        ]
    )

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.mtbf_days == 10.0


# -- mttr_hours --------------------------------------------------------------


def test_mttr_is_none_when_no_cm_report_has_downtime_hours():
    knowledge = _knowledge(cm_history=[{"cm_report_code": "CM-1", "downtime_hours": None}])

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.mttr_hours is None


def test_mttr_averages_downtime_hours_across_cm_reports_that_recorded_one():
    knowledge = _knowledge(
        cm_history=[
            {"cm_report_code": "CM-1", "downtime_hours": 4},
            {"cm_report_code": "CM-2", "downtime_hours": 8},
            {"cm_report_code": "CM-3", "downtime_hours": None},
        ]
    )

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.mttr_hours == 6.0


# -- pm_compliance_rate -------------------------------------------------------


def test_pm_compliance_is_zero_when_no_pm_schedules_exist():
    knowledge = _knowledge(pm_schedules=[])

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.pm_compliance_rate == 0


def test_pm_compliance_is_100_when_no_schedule_is_overdue():
    knowledge = _knowledge(
        pm_schedules=[
            {"pm_schedule_code": "PM-1", "next_due": "2026-09-01"},
            {"pm_schedule_code": "PM-2", "next_due": "2026-10-01"},
        ]
    )

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.pm_compliance_rate == 100


def test_pm_compliance_counts_next_due_before_today_as_overdue():
    knowledge = _knowledge(
        pm_schedules=[
            {"pm_schedule_code": "PM-1", "next_due": "2026-07-01"},  # overdue
            {"pm_schedule_code": "PM-2", "next_due": "2026-09-01"},  # not overdue
        ]
    )

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.pm_compliance_rate == 50


def test_pm_compliance_treats_a_missing_next_due_as_not_overdue():
    knowledge = _knowledge(pm_schedules=[{"pm_schedule_code": "PM-1", "next_due": None}])

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.pm_compliance_rate == 100


# -- breakdown_count -----------------------------------------------------------


def test_breakdown_count_is_zero_when_breakdown_history_is_empty():
    knowledge = _knowledge(breakdown_history=[])

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.breakdown_count == 0


def test_breakdown_count_is_the_length_of_breakdown_history():
    knowledge = _knowledge(
        breakdown_history=[{"maintenance_record_code": "MH-1"}, {"maintenance_record_code": "MH-2"}]
    )

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.breakdown_count == 2


# -- critical_spare_count ------------------------------------------------------


def test_critical_spare_count_is_zero_when_inventory_is_empty():
    knowledge = _knowledge(inventory=[])

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.critical_spare_count == 0


def test_critical_spare_count_counts_zero_and_unknown_quantity_as_critical():
    knowledge = _knowledge(
        inventory=[
            {"seal_code": "SC-001", "quantity_on_hand": 0},
            {"seal_code": "SC-002", "quantity_on_hand": None},
            {"seal_code": "SC-003", "quantity_on_hand": 4},
        ]
    )

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.critical_spare_count == 2


def test_critical_spare_count_treats_string_quantities_with_the_same_stock_rule():
    knowledge = _knowledge(
        inventory=[
            {"seal_code": "SC-001", "quantity_on_hand": "0"},
            {"seal_code": "SC-002", "quantity_on_hand": "  "},
            {"seal_code": "SC-003", "quantity_on_hand": "2"},
        ]
    )

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert metrics.critical_spare_count == 2


# -- overall shape / determinism ------------------------------------------------


def test_returns_an_executive_metrics_instance_carrying_the_tag():
    knowledge = _knowledge()

    metrics = compute_executive_metrics(knowledge, today=TODAY)

    assert isinstance(metrics, ExecutiveMetrics)
    assert metrics.tag_number == TAG


def test_defaults_today_to_the_real_date_when_not_injected():
    # Proves the `today` parameter is genuinely optional (matching
    # get_pump_condition_monitoring_flag's own injectable-`today`
    # convention) without asserting on the real clock's value.
    knowledge = _knowledge()

    metrics = compute_executive_metrics(knowledge)

    assert isinstance(metrics, ExecutiveMetrics)


def test_is_deterministic_across_repeated_calls():
    knowledge = _knowledge(
        cm_history=[
            {"cm_report_code": "CM-1", "created_at": "2026-06-01T00:00:00Z", "downtime_hours": 4},
            {"cm_report_code": "CM-2", "created_at": "2026-06-11T00:00:00Z", "downtime_hours": 8},
        ],
        breakdown_history=[{"maintenance_record_code": "MH-1"}],
        pm_schedules=[{"pm_schedule_code": "PM-1", "next_due": "2026-07-01"}],
        inventory=[{"seal_code": "SC-001", "quantity_on_hand": 0}],
        recommendation=(_recommendation(priority=90),),
    )

    first = compute_executive_metrics(knowledge, today=TODAY)
    second = compute_executive_metrics(knowledge, today=TODAY)

    assert first == second


# -- no duplicated aggregate / no gateway access --------------------------------


def test_module_makes_no_gateway_or_sql_calls():
    source = Path(__file__).resolve().parents[1].joinpath("executive_metrics.py").read_text(encoding="utf-8")
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("import ", "from "))]
    for forbidden in ("Gateway", "sqlite3", "fastapi", "APIRouter"):
        assert not any(forbidden in line for line in import_lines)


def test_module_reuses_ltsa_knowledge_type_not_a_redefinition():
    source = Path(__file__).resolve().parents[1].joinpath("executive_metrics.py").read_text(encoding="utf-8")
    assert "from .ltsa_knowledge_service import" in source or "from API.ltsa_knowledge_service import" in source
    assert "class LTSAKnowledge" not in source

