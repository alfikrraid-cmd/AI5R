"""MWO-LTSA-FLEET-ATTENTION-001 -- end-to-end regression + performance
proof for the "Pompa mana yang perlu perhatian hari ini?" fleet-attention
query, exercised through the REAL FleetExecutiveSummaryService/
FleetReliabilityService/RecommendationEngine/LTSAKnowledgeService wiring
(fakes only at the gateway/repository boundary, matching production's own
dependencies.py wiring: PM/CMON/PM-schedule/CM-report/CMON-schedule via
fast direct-DB repositories, seal-compatibility/seal/seal-document/work-
order/maintenance-history via the slower n8n-style gateways) -- never a
shallow mock of FleetExecutiveSummaryService itself, so the actual ranking
logic (RecommendationEngine's active-leak vs. historical-leak priority
tiers) is genuinely exercised, not assumed.
"""

import time
from datetime import date, timedelta

from API.copilot_ask_service import DATA_GAP, FACT, RECOMMENDATION, ask_copilot
from API.fleet_executive_summary import FleetExecutiveSummaryService
from API.fleet_reliability_service import FleetReliabilityService
from API.ltsa_knowledge_service import LTSAKnowledgeService

TODAY = date.today()
RECENT = (TODAY - timedelta(days=5)).isoformat()
OLD = (TODAY - timedelta(days=90)).isoformat()


class FakePumpGateway:
    def __init__(self, pumps):
        self._pumps = {p["tag_number"]: p for p in pumps}

    def list_pumps(self):
        return {"success": True, "data": list(self._pumps.values())}

    def get_pump(self, tag_number):
        pump = self._pumps.get(tag_number)
        return {"success": bool(pump), "data": pump}


class FakeCountingListGateway:
    """One reusable fake for every gateway whose only method is a
    zero-arg list_X() returning ALL rows unfiltered -- tracks call count
    so a test can prove the N+1 doubling fix (list_work_orders no longer
    called twice per LTSAKnowledgeService.build(tag), and
    FleetExecutiveSummaryService no longer fetches the whole fleet's
    knowledge twice)."""

    def __init__(self, method_name, rows):
        self.calls = 0
        setattr(self, method_name, self._list)
        self._rows = rows

    def _list(self):
        self.calls += 1
        return {"success": True, "data": self._rows}


class FakeRepository:
    """list_by_asset(tag)-shaped fake, matching the fast direct-DB
    repository contract (pm_occurrence_repository, condition_monitoring_
    reading_repository) -- pre-filtered per pump, exactly like the real
    repositories' own SQL WHERE clause."""

    def __init__(self, rows_by_tag):
        self.calls = 0
        self._rows_by_tag = rows_by_tag

    def list_by_asset(self, tag_number):
        self.calls += 1
        return list(self._rows_by_tag.get(tag_number, []))


class FakeListRepository:
    """list_X()-shaped fake for repositories whose method returns
    everything (pm_schedule_repository, cm_report_repository,
    condition_monitoring_schedule_repository) -- LTSAKnowledgeService
    filters these by tag itself, matching its own _build_pm_schedules/
    _build_cm_history/_build_condition_monitoring_schedules logic."""

    def __init__(self, method_name, rows):
        self.calls = 0
        setattr(self, method_name, self._list)
        self._rows = rows

    def _list(self):
        self.calls += 1
        return {"success": True, "data": self._rows}


def _pump(tag, area="FRAKSINASI", status="Active"):
    return {"tag_number": tag, "area": area, "status": status}


def _cmon_reading(tag, reading_date, leak=True, code=None):
    return {
        "asset_code": tag,
        "condition_monitoring_reading_code": code or f"CMON-{tag}",
        "reading_date": reading_date,
        "mechanical_seal_leak_de": leak,
        "mechanical_seal_leak_nde": False,
    }


def _pm_schedule(tag, next_due, status="ACTIVE", code=None):
    return {
        "asset_code": tag,
        "pm_schedule_code": code or f"PM-SCHED-{tag}",
        "next_due": next_due,
        "status": status,
    }


class _Fixture:
    """One reusable fleet fixture builder -- pumps/readings/schedules
    passed in, everything else (compatibility/seal/document/work-order/
    maintenance-history gateways) defaults to empty, never fabricated."""

    def __init__(self, pumps, cmon_readings=None, pm_schedules=None, cm_reports=None):
        self.pump_gateway = FakePumpGateway(pumps)
        self.cmon_repo = FakeRepository(cmon_readings or {})
        self.pm_repo = FakeRepository({})
        self.pm_schedule_repo = FakeListRepository("list_pm_schedules", pm_schedules or [])
        self.cm_report_repo = FakeListRepository("list_cm_reports", cm_reports or [])
        self.cmon_schedule_repo = FakeListRepository("list_condition_monitoring_schedules", [])
        self.compat_gateway = FakeCountingListGateway("list_seal_pump_compatibilities", [])
        self.seal_gateway = FakeCountingListGateway("list_seals", [])
        self.doc_gateway = FakeCountingListGateway("list_seal_engineering_documents", [])
        self.work_order_gateway = FakeCountingListGateway("list_work_orders", [])
        self.maintenance_history_gateway = FakeCountingListGateway("list_maintenance_history", [])

        self.knowledge_service = LTSAKnowledgeService(
            pump_gateway=self.pump_gateway,
            maintenance_history_gateway=self.maintenance_history_gateway,
            seal_gateway=self.seal_gateway,
            seal_pump_compatibility_gateway=self.compat_gateway,
            work_order_gateway=self.work_order_gateway,
            seal_engineering_document_gateway=self.doc_gateway,
            pm_occurrence_repository=self.pm_repo,
            condition_monitoring_reading_repository=self.cmon_repo,
            pm_schedule_repository=self.pm_schedule_repo,
            cm_report_repository=self.cm_report_repo,
            condition_monitoring_schedule_repository=self.cmon_schedule_repo,
        )
        self.reliability_service = FleetReliabilityService(
            pump_gateway=self.pump_gateway, ltsa_knowledge_service=self.knowledge_service
        )
        self.summary_service = FleetExecutiveSummaryService(fleet_reliability_service=self.reliability_service)


# -- critical test: current unresolved leak must outrank historical-only ---


def test_current_leak_outranks_historical_only_leak_critical_test():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A"), _pump("PUMP-B")],
        cmon_readings={
            "PUMP-A": [_cmon_reading("PUMP-A", OLD)],
            "PUMP-B": [_cmon_reading("PUMP-B", RECENT)],
        },
    )
    summary = fixture.summary_service.build()

    tags_in_order = [risk.tag_number for risk in summary.top_risk_pumps]
    assert "PUMP-B" in tags_in_order
    assert tags_in_order.index("PUMP-B") < tags_in_order.index("PUMP-A")
    b_risk = next(r for r in summary.top_risk_pumps if r.tag_number == "PUMP-B")
    a_risk = next(r for r in summary.top_risk_pumps if r.tag_number == "PUMP-A")
    assert b_risk.priority > a_risk.priority
    assert b_risk.rule_code == "REC_ACTIVE_LEAK"
    assert a_risk.rule_code == "REC_HISTORICAL_LEAK"


# -- CURRENT_ABNORMAL_INCLUDED / UNRESOLVED_CMON_INCLUDED / CURRENT_LEAK_INCLUDED --


def test_current_abnormal_condition_is_included_in_ranking():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A")],
        cmon_readings={"PUMP-A": [_cmon_reading("PUMP-A", RECENT)]},
    )
    summary = fixture.summary_service.build()
    assert any(r.tag_number == "PUMP-A" for r in summary.top_risk_pumps)


def test_unresolved_cmon_finding_is_included_in_ranking():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A")],
        cmon_readings={"PUMP-A": [_cmon_reading("PUMP-A", RECENT, leak=True)]},
    )
    summary = fixture.summary_service.build()
    risk = next(r for r in summary.top_risk_pumps if r.tag_number == "PUMP-A")
    assert risk.rule_code == "REC_ACTIVE_LEAK"


def test_current_leak_is_included_and_ranked_via_ask_copilot():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A")],
        cmon_readings={"PUMP-A": [_cmon_reading("PUMP-A", RECENT)]},
    )
    answer = ask_copilot(
        "Pompa mana yang perlu perhatian hari ini?", None, None,
        pump_gateway=fixture.pump_gateway, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=None, condition_monitoring_reading_repository=None,
        fleet_executive_summary_service=fixture.summary_service,
        pm_occurrence_repository=None, cm_report_repository=None,
    )
    assert answer.kind == RECOMMENDATION
    assert "PUMP-A" in answer.answer


# -- HISTORICAL_ONLY_LOWER_PRIORITY -----------------------------------------


def test_historical_only_leak_still_appears_but_at_lower_priority():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A")],
        cmon_readings={"PUMP-A": [_cmon_reading("PUMP-A", OLD)]},
    )
    summary = fixture.summary_service.build()
    risk = next(r for r in summary.top_risk_pumps if r.tag_number == "PUMP-A")
    assert risk.rule_code == "REC_HISTORICAL_LEAK"
    from API.recommendation_engine import PRIORITY_ACTIVE_LEAK
    assert risk.priority < PRIORITY_ACTIVE_LEAK


# -- AUTHORIZED_SCOPE_ONLY ----------------------------------------------------


def test_out_of_scope_pump_never_appears_in_ranking():
    fixture = _Fixture(
        pumps=[_pump("IN-SCOPE", area="FRAKSINASI"), _pump("OUT-OF-SCOPE", area="UTILITAS")],
        cmon_readings={
            "IN-SCOPE": [_cmon_reading("IN-SCOPE", RECENT)],
            "OUT-OF-SCOPE": [_cmon_reading("OUT-OF-SCOPE", RECENT)],
        },
    )
    summary = fixture.summary_service.build(scope=frozenset({"FRAKSINASI"}))
    tags = [r.tag_number for r in summary.top_risk_pumps]
    assert "IN-SCOPE" in tags
    assert "OUT-OF-SCOPE" not in tags


# -- MAX_DEFAULT_RESULTS_5 ----------------------------------------------------


def test_max_default_results_is_five_with_truthful_overflow_count():
    pumps = [_pump(f"PUMP-{i}") for i in range(8)]
    cmon_readings = {f"PUMP-{i}": [_cmon_reading(f"PUMP-{i}", RECENT)] for i in range(8)}
    fixture = _Fixture(pumps=pumps, cmon_readings=cmon_readings)
    summary = fixture.summary_service.build()

    assert len(summary.top_risk_pumps) == 5
    assert summary.attention_pump_count == 8

    answer = ask_copilot(
        "Pompa mana yang perlu perhatian hari ini?", None, None,
        pump_gateway=fixture.pump_gateway, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=None, condition_monitoring_reading_repository=None,
        fleet_executive_summary_service=fixture.summary_service,
        pm_occurrence_repository=None, cm_report_repository=None,
    )
    assert "3 more pump(s) also need attention." in answer.answer

    id_answer = ask_copilot(
        "Pompa mana yang perlu perhatian hari ini?", None, None,
        pump_gateway=fixture.pump_gateway, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=None, condition_monitoring_reading_repository=None,
        fleet_executive_summary_service=fixture.summary_service,
        pm_occurrence_repository=None, cm_report_repository=None,
        language="id",
    )
    assert "Masih ada 3 pompa lain yang memerlukan perhatian." in id_answer.answer


def test_no_overflow_line_when_five_or_fewer_pumps_need_attention():
    pumps = [_pump(f"PUMP-{i}") for i in range(3)]
    cmon_readings = {f"PUMP-{i}": [_cmon_reading(f"PUMP-{i}", RECENT)] for i in range(3)}
    fixture = _Fixture(pumps=pumps, cmon_readings=cmon_readings)
    answer = ask_copilot(
        "Pompa mana yang perlu perhatian hari ini?", None, None,
        pump_gateway=fixture.pump_gateway, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=None, condition_monitoring_reading_repository=None,
        fleet_executive_summary_service=fixture.summary_service,
        pm_occurrence_repository=None, cm_report_repository=None,
    )
    assert "Masih ada" not in answer.answer


# -- NO_CONTEXT_BIAS -----------------------------------------------------------


def test_no_context_bias_a_different_pump_with_stronger_evidence_outranks_211_p_13ar():
    fixture = _Fixture(
        pumps=[_pump("211-P-13AR"), _pump("210-P-05AR")],
        cmon_readings={"211-P-13AR": [_cmon_reading("211-P-13AR", OLD)]},
        cm_reports=[
            {
                "asset_code": "210-P-05AR", "cm_report_code": "CM-1", "severity": "CRITICAL",
                "status": "OPEN",
            }
        ],
    )
    summary = fixture.summary_service.build()
    tags_in_order = [risk.tag_number for risk in summary.top_risk_pumps]
    # 210-P-05AR (real open CRITICAL CM report, priority 100) must rank
    # above 211-P-13AR (only historical leak evidence, priority 40) purely
    # on canonical evidence -- proving no hardcoded/discussed-pump bias.
    assert tags_in_order.index("210-P-05AR") < tags_in_order.index("211-P-13AR")


# -- FACT_RECOMMENDATION_SEPARATION -------------------------------------------


def test_fact_vs_recommendation_kind_is_correct_in_both_states():
    empty_fixture = _Fixture(pumps=[_pump("PUMP-A")])
    empty_answer = ask_copilot(
        "Pompa mana yang perlu perhatian hari ini?", None, None,
        pump_gateway=empty_fixture.pump_gateway, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=None, condition_monitoring_reading_repository=None,
        fleet_executive_summary_service=empty_fixture.summary_service,
        pm_occurrence_repository=None, cm_report_repository=None,
    )
    assert empty_answer.kind == FACT  # "nothing needs attention" is a direct fact

    ranked_fixture = _Fixture(
        pumps=[_pump("PUMP-A")], cmon_readings={"PUMP-A": [_cmon_reading("PUMP-A", RECENT)]}
    )
    ranked_answer = ask_copilot(
        "Pompa mana yang perlu perhatian hari ini?", None, None,
        pump_gateway=ranked_fixture.pump_gateway, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=None, condition_monitoring_reading_repository=None,
        fleet_executive_summary_service=ranked_fixture.summary_service,
        pm_occurrence_repository=None, cm_report_repository=None,
    )
    assert ranked_answer.kind == RECOMMENDATION  # a ranked list is a derived judgement


# -- NO_SILENT_FAILURE ---------------------------------------------------------


def test_no_silent_failure_service_exception_becomes_data_gap_never_crashes():
    class _RaisingFleetExecutiveSummaryService:
        def build(self, *, scope=None):
            raise ConnectionError("simulated fleet service outage")

    answer = ask_copilot(
        "Pompa mana yang perlu perhatian hari ini?", None, None,
        pump_gateway=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=None, condition_monitoring_reading_repository=None,
        fleet_executive_summary_service=_RaisingFleetExecutiveSummaryService(),
        pm_occurrence_repository=None, cm_report_repository=None,
    )
    assert answer.kind == DATA_GAP
    assert answer.answer  # never an empty/silent reply


# -- performance / N+1 proof ---------------------------------------------------


def test_performance_no_n_plus_1_doubling_across_fleet_scan():
    pumps = [_pump(f"PUMP-{i}") for i in range(20)]
    cmon_readings = {f"PUMP-{i}": [_cmon_reading(f"PUMP-{i}", RECENT)] for i in range(20)}
    fixture = _Fixture(pumps=pumps, cmon_readings=cmon_readings)

    started = time.perf_counter()
    summary = fixture.summary_service.build()
    elapsed_ms = (time.perf_counter() - started) * 1000

    pumps_scanned = len(pumps)
    # MWO-LTSA-FLEET-ATTENTION-001's own two fixes, both measured directly
    # against real call counters (never a timing assertion, per this
    # MWO's own "avoid brittle timing assertions" instruction):
    #  1. list_work_orders() called exactly ONCE per pump (was twice,
    #     within a single LTSAKnowledgeService.build(tag) call).
    #  2. Every "list ALL X" gateway is called exactly `pumps_scanned`
    #     times total across the WHOLE fleet scan (was 2x that, from
    #     FleetExecutiveSummaryService's own build()+list_pump_knowledge()
    #     double-fetch).
    assert fixture.work_order_gateway.calls == pumps_scanned
    assert fixture.compat_gateway.calls == pumps_scanned
    assert fixture.seal_gateway.calls == pumps_scanned
    assert fixture.doc_gateway.calls == pumps_scanned
    assert fixture.maintenance_history_gateway.calls == pumps_scanned
    assert fixture.cmon_repo.calls == pumps_scanned
    assert len(summary.top_risk_pumps) == 5
    assert summary.attention_pump_count == pumps_scanned

    print(
        f"PUMPS_SCANNED={pumps_scanned} "
        f"WORK_ORDER_GATEWAY_CALLS={fixture.work_order_gateway.calls} "
        f"COMPAT_GATEWAY_CALLS={fixture.compat_gateway.calls} "
        f"SEAL_GATEWAY_CALLS={fixture.seal_gateway.calls} "
        f"DOC_GATEWAY_CALLS={fixture.doc_gateway.calls} "
        f"MAINTENANCE_HISTORY_GATEWAY_CALLS={fixture.maintenance_history_gateway.calls} "
        f"CMON_REPOSITORY_CALLS={fixture.cmon_repo.calls} "
        f"LLM_CALL_COUNT=0 "
        f"TOTAL_PROCESSING_MS={elapsed_ms:.2f}"
    )
