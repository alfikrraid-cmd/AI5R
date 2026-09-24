"""LTSA_CM_UI_REMEDIATION_R1B -- Current Condition consumers read the canonical
latest valid occurrence (cm_condition_evaluator.current_leak_condition), while
RECENT_LEAK_OBSERVED keeps its time window. Covers the shared cm_summary
builder, EngineeringContextEngine, RecommendationEngine, fleet current-leak
pumps and the seal diagnostic."""

import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API import maintenance_intelligence_service as mis  # noqa: E402
from API.cm_condition_evaluator import current_leak_condition  # noqa: E402
from API.engineering_context_engine import EngineeringContextEngine  # noqa: E402
from API.fleet_analytics_service import current_leak_pumps  # noqa: E402
from API.ltsa_knowledge_service import LTSAKnowledge  # noqa: E402
from API.recommendation_engine import RecommendationEngine  # noqa: E402
from API.seal_leak_diagnostic_service import _collect_leak_evidence  # noqa: E402

TODAY = date(2026, 9, 24)


def _day(days_ago):
    return (TODAY - timedelta(days=days_ago)).isoformat()


def _r(code, days_ago, *, de=None, nde=None, status="FINALIZED", tag="P-1", **extra):
    row = {
        "condition_monitoring_reading_code": code, "asset_code": tag, "reading_date": _day(days_ago),
        "created_at": f"{_day(days_ago)}T01:00:00Z", "workflow_status": status, "deleted_at": None,
        "mechanical_seal_leak_de": de, "mechanical_seal_leak_nde": nde, "suction_temp": 100.0,
        "finding": None,
    }
    row.update(extra)
    return row


def _summary(readings):
    return mis.build_cm_leak_summary(readings, today=TODAY)


# -- CURRENT_ACTIVE_LEAK vs RECENT_LEAK_OBSERVED --------------------------------


@pytest.mark.parametrize(
    "readings, current, recent",
    [
        ([_r("OLD", 25, de=True), _r("NOW", 0, de=False, nde=False)], False, True),
        ([_r("OLD", 40, de=True), _r("NOW", 0, de=False, nde=False)], False, False),
        ([_r("NOW", 0, de=True)], True, True),
        ([_r("OLD", 90, de=True)], True, False),  # latest occurrence is a leak: current, not recent
    ],
    ids=["leak-25d-then-clear", "leak-40d-then-clear", "leak-today", "latest-leak-90d"],
)
def test_current_active_leak_is_separate_from_recent_leak_observed(readings, current, recent):
    summary = _summary(readings)
    assert summary["current_active_leak"] is current
    assert summary["leak_flag"] is current  # REC_ACTIVE_LEAK input = CURRENT_ACTIVE_LEAK
    assert summary["recent_leak_observed"] is recent
    assert summary["recent_leak_window_days"] == 30


@pytest.mark.parametrize(
    "readings, state, active, code",
    [
        ([_r("A", 10, de=True), _r("B", 1, de=False, nde=False)], "NO_LEAK", False, "B"),
        ([_r("A", 10, de=False, nde=False), _r("B", 1, de=True, nde=None)], "LEAK_DE", True, "B"),
        ([_r("A", 10, de=True, nde=True), _r("B", 1, de=None, nde=None)], "UNKNOWN", False, "B"),
        ([_r("A", 10, de=True), _r("B", 1, de=False, nde=None)], "NO_LEAK_DE_ONLY", False, "B"),
        ([_r("A", 10, de=True), _r("B", 1, de=None, nde=False)], "NO_LEAK_NDE_ONLY", False, "B"),
        ([_r("FIN", 10, de=False, nde=False), _r("DRF", 1, de=True, status="DRAFT")], "LEAK_DE", True, "DRF"),
        ([_r("FIN", 10, de=True), _r("DEL", 1, de=False, nde=False, deleted_at="2026-09-24T00:00:00")], "LEAK_DE", True, "FIN"),
        ([_r("FIN", 10, de=True), _r("BAD", 1, de=False, nde=False, reading_date="2026-02-31")], "LEAK_DE", True, "FIN"),
    ],
    ids=["older-leak-latest-clear", "older-clear-latest-de", "latest-unknown-no-fallback", "latest-de-only",
         "latest-nde-only", "newer-draft", "newer-deleted-excluded", "newer-invalid-date-excluded"],
)
def test_summary_preserves_canonical_current_state(readings, state, active, code):
    summary = _summary(readings)
    assert summary["current_leak_state"] == state
    assert summary["current_active_leak"] is active
    condition = summary["current_leak_condition"]
    assert condition["reading_code"] == code and condition["state"] == state
    assert condition == current_leak_condition(readings)
    if active:
        assert summary["latest_abnormal_values"]["reading_code"] == code
    else:
        assert summary["latest_abnormal_values"] is None


def test_summary_exposes_workflow_status_and_raw_tristate():
    condition = _summary([_r("DRF", 1, de=None, nde=False, status="DRAFT")])["current_leak_condition"]
    assert condition["workflow_status"] == "DRAFT"
    assert condition["de"] is None and condition["nde"] is False
    assert condition["completeness"] == "PARTIAL" and condition["has_current_reading"] is True


# -- EngineeringContextEngine (Knowledge summary) --------------------------------


class _EmptyReports:
    def list_cm_reports(self):
        return {"success": True, "data": []}


class _RaisingGateway:
    def list_condition_monitoring_readings(self):
        raise AssertionError("readings were supplied; the gateway must not be called")


class _ListGateway:
    def __init__(self, rows):
        self.rows = rows

    def list_condition_monitoring_readings(self):
        return {"success": True, "data": self.rows}


def _engine(gateway):
    return EngineeringContextEngine(cm_report_gateway=_EmptyReports(), condition_monitoring_reading_gateway=gateway)


def test_context_engine_uses_supplied_readings_and_current_semantics():
    readings = [_r("OLD", 5, de=True), _r("NOW", 0, de=False, nde=False)]
    cm_summary, evidence = _engine(_RaisingGateway())._build_cm_summary("P-1", readings)
    assert cm_summary["overall_condition"] == "NORMAL"  # recent leak alone is not the current state
    assert cm_summary["leak_flag"] is False and cm_summary["current_active_leak"] is False
    assert cm_summary["recent_leak_observed"] is True
    assert cm_summary["current_leak_state"] == "NO_LEAK"
    assert evidence == []


def test_context_engine_active_current_leak_is_abnormal_with_evidence():
    readings = [_r("OLD", 5, de=False, nde=False), _r("NOW", 0, de=True, nde=True)]
    cm_summary, evidence = _engine(_RaisingGateway())._build_cm_summary("P-1", readings)
    assert cm_summary["overall_condition"] == "ABNORMAL"
    assert cm_summary["current_leak_state"] == "LEAK_DE_AND_NDE"
    assert evidence[0]["flag"] == "CM_ABNORMAL" and evidence[0]["reference"] == "NOW"


def test_context_engine_falls_back_to_gateway_readings_for_the_tag():
    rows = [_r("OTHER", 0, de=True, tag="P-2"), _r("MINE", 0, de=False, nde=False, tag="P-1")]
    cm_summary, _ = _engine(_ListGateway(rows))._build_cm_summary("P-1")
    assert cm_summary["current_leak_condition"]["reading_code"] == "MINE"
    assert cm_summary["current_active_leak"] is False


# -- RecommendationEngine --------------------------------------------------------


def _knowledge(readings):
    return LTSAKnowledge(
        tag_number="P-1", pump=None, seal=[], inventory=[], pm_history=[], cm_history=[],
        breakdown_history=[], drawings=[], recommendation=(), pm_schedules=[],
        condition_monitoring_schedules=[], condition_monitoring_readings=readings,
    )


def test_recent_but_superseded_leak_is_not_rec_active_leak():
    readings = [_r("OLD", 5, de=True), _r("NOW", 0, de=False, nde=False)]
    codes = [r.rule_code for r in RecommendationEngine().recommend(_knowledge(readings), {"cm_summary": _summary(readings)})]
    assert "REC_ACTIVE_LEAK" not in codes
    assert "REC_HISTORICAL_LEAK" in codes  # still visible as history


def test_current_leak_is_rec_active_leak_citing_the_current_reading():
    readings = [_r("OLD", 5, de=False, nde=False), _r("NOW", 0, de=None, nde=True)]
    recs = RecommendationEngine().recommend(_knowledge(readings), {"cm_summary": _summary(readings)})
    active = next(r for r in recs if r.rule_code == "REC_ACTIVE_LEAK")
    assert [(e.reference, e.field) for e in active.evidence] == [("NOW", "mechanical_seal_leak_nde")]


# -- Fleet current-leak pumps / copilot "leaking now" ----------------------------


def test_fleet_current_leak_pumps_follow_latest_valid_occurrence():
    batch = SimpleNamespace(
        pumps=[{"tag_number": t} for t in ("SUPERSEDED", "ACTIVE", "OLD-ACTIVE", "UNKNOWN", "NONE")],
        cmon_by_tag={
            "SUPERSEDED": (_r("S1", 5, de=True, tag="SUPERSEDED"), _r("S2", 0, de=False, nde=False, tag="SUPERSEDED")),
            "ACTIVE": (_r("A1", 1, de=True, tag="ACTIVE", finding="Bocor DE"),),
            "OLD-ACTIVE": (_r("O1", 200, nde=True, tag="OLD-ACTIVE"),),
            "UNKNOWN": (_r("U1", 5, de=True, tag="UNKNOWN"), _r("U2", 0, tag="UNKNOWN")),
        },
    )
    rows = current_leak_pumps(batch, today=TODAY)
    assert [row.equipment_tag for row in rows] == ["ACTIVE", "OLD-ACTIVE"]
    assert rows[0].finding == "Bocor DE" and rows[0].workflow_status == "FINALIZED"
    for tag in ("SUPERSEDED", "ACTIVE", "OLD-ACTIVE", "UNKNOWN", "NONE"):
        assert (tag in {r.equipment_tag for r in rows}) is current_leak_condition(list(batch.cmon_by_tag.get(tag, ())))["active"]


# -- Seal diagnostic ---------------------------------------------------------------


def test_seal_diagnostic_separates_current_recent_and_historical():
    readings = [_r("H1", 100, de=True), _r("R1", 10, nde=True), _r("NOW", 0, de=False, nde=False)]
    evidence, current, historical = _collect_leak_evidence(readings, today=TODAY)
    assert current is False and evidence["current_leak_flag"] is False
    assert evidence["current_leak_state"] == "NO_LEAK"
    assert evidence["recent_leak_observed"] is True
    assert historical == 1 and evidence["historical_leak_count"] == 1
    assert evidence["latest_leak_finding"] is None


def test_seal_diagnostic_current_leak_cites_current_reading():
    readings = [_r("H1", 100, de=True), _r("NOW", 0, de=True, finding="Seal bocor")]
    evidence, current, historical = _collect_leak_evidence(readings, today=TODAY)
    assert current is True and evidence["current_leak_state"] == "LEAK_DE"
    assert evidence["latest_leak_finding"]["source"] == "NOW"
    assert evidence["latest_leak_finding"]["finding"] == "Seal bocor"
    assert historical == 1


# -- RECENT_LEAK_OBSERVED endpoint keeps its meaning ------------------------------


def test_condition_monitoring_flag_endpoint_stays_recent_leak_observed():
    rows = [_r("OLD", 5, de=True), _r("NOW", 0, de=False, nde=False)]
    result = mis.get_pump_condition_monitoring_flag("P-1", condition_monitoring_reading_gateway=_ListGateway(rows), today=TODAY)
    assert result["semantic"] == "RECENT_LEAK_OBSERVED"
    assert result["flagged"] is True and result["recent_leak_observed"] is True
    assert result["latest_flagged_reading"]["condition_monitoring_reading_code"] == "OLD"
