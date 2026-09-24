"""LTSA_CM_UI_REMEDIATION_R1A -- canonical leak states, active-leak helper and
authoritative Current Condition selection (cm_condition_evaluator)."""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API import maintenance_intelligence_service as mis  # noqa: E402
from API.cm_condition_evaluator import (  # noqa: E402
    CURRENT_CONDITION_STATUSES,
    ELIGIBLE_STATUSES,
    LEAK_STATES,
    canonical_leak_state,
    current_leak_condition,
    evaluate_current_condition,
    evaluate_leak,
    is_active_leak,
    is_current_condition_candidate,
    select_current_condition_cm,
    select_latest_valid_cm,
)

TRUTH_TABLE = {
    (True, True): "LEAK_DE_AND_NDE",
    (True, False): "LEAK_DE",
    (True, None): "LEAK_DE",
    (False, True): "LEAK_NDE",
    (None, True): "LEAK_NDE",
    (False, False): "NO_LEAK",
    (False, None): "NO_LEAK_DE_ONLY",
    (None, False): "NO_LEAK_NDE_ONLY",
    (None, None): "UNKNOWN",
}


def _reading(code, reading_date, *, de=None, nde=None, status="FINALIZED", created_at="2026-01-01T00:00:00Z", **extra):
    base = {
        "condition_monitoring_reading_code": code,
        "asset_code": "701-P-1A",
        "reading_date": reading_date,
        "created_at": created_at,
        "workflow_status": status,
        "deleted_at": None,
        "provenance": "MANUAL",
        "mechanical_seal_leak_de": de,
        "mechanical_seal_leak_nde": nde,
        "suction_temp": 230.0,
    }
    base.update(extra)
    return base


# -- occurrence state ----------------------------------------------------------


@pytest.mark.parametrize("values, state", sorted(TRUTH_TABLE.items(), key=str))
def test_canonical_occurrence_truth_table(values, state):
    assert canonical_leak_state(*values) == state
    assert evaluate_leak(*values)["state"] == state


def test_truth_table_covers_every_canonical_state():
    assert set(TRUTH_TABLE.values()) == set(LEAK_STATES)


@pytest.mark.parametrize("de, nde", [(None, None), (False, None), (None, False)])
def test_null_and_partial_are_never_confirmed_no_leak(de, nde):
    assert canonical_leak_state(de, nde) != "NO_LEAK"
    assert evaluate_leak(de, nde)["completeness"] != "COMPLETE"


@pytest.mark.parametrize("value", ["", 0, 1, "Y", "N", "true"])
def test_only_literal_booleans_are_recorded(value):
    assert canonical_leak_state(value, None) == "UNKNOWN"
    assert canonical_leak_state(None, value) == "UNKNOWN"


def test_legacy_status_vocabulary_is_unchanged_for_existing_callers():
    legacy = {
        (True, True): "LEAK_DE_NDE", (True, False): "LEAK_DE", (False, True): "LEAK_NDE",
        (False, False): "NO_LEAK", (True, None): "LEAK_DE", (None, True): "LEAK_NDE",
        (False, None): "NO_LEAK_DE", (None, False): "NO_LEAK_NDE", (None, None): "NOT_RECORDED",
    }
    for values, status in legacy.items():
        result = evaluate_leak(*values)
        assert result["status"] == status
        assert result["de"] is values[0] and result["nde"] is values[1]


@pytest.mark.parametrize("state", LEAK_STATES)
def test_is_active_leak_only_for_leak_states(state):
    assert is_active_leak(state) is (state in {"LEAK_DE", "LEAK_NDE", "LEAK_DE_AND_NDE"})


# -- Current Condition: latest valid occurrence decides ------------------------


def test_older_leak_then_latest_no_leak_is_not_active():
    readings = [_reading("A", "2026-01-10", de=True), _reading("B", "2026-02-10", de=False, nde=False)]
    current = current_leak_condition(readings)
    assert current["state"] == "NO_LEAK" and current["active"] is False and current["reading_code"] == "B"


def test_older_no_leak_then_latest_de_leak_is_active():
    readings = [_reading("A", "2026-01-10", de=False, nde=False), _reading("B", "2026-02-10", de=True, nde=None)]
    current = current_leak_condition(readings)
    assert current["state"] == "LEAK_DE" and current["active"] is True
    assert current["de"] is True and current["nde"] is None and current["completeness"] == "PARTIAL"


def test_latest_unknown_leak_never_falls_back_to_older_leak():
    readings = [_reading("A", "2026-01-10", de=True, nde=True), _reading("B", "2026-02-10", de=None, nde=None)]
    current = current_leak_condition(readings)
    assert current["reading_code"] == "B"  # still valid: it carries suction_temp
    assert current["state"] == "UNKNOWN" and current["active"] is False


def test_history_still_shows_the_older_leak():
    older = _reading("A", "2026-01-10", de=True)
    readings = [older, _reading("B", "2026-02-10", de=False, nde=False)]
    assert current_leak_condition(readings)["active"] is False
    assert evaluate_leak(older["mechanical_seal_leak_de"], older["mechanical_seal_leak_nde"])["state"] == "LEAK_DE"


def test_no_valid_occurrence_is_unknown_and_inactive():
    readings = [_reading("A", "2026-01-10", de=True, status="DRAFT")]
    current = current_leak_condition(readings)
    assert current == {
        "reading_code": None, "reading_date": None, "workflow_status": None,
        "state": "UNKNOWN", "active": False, "de": None, "nde": None,
        "completeness": "NOT_RECORDED", "has_current_reading": False,
    }
    assert current_leak_condition([])["state"] == "UNKNOWN"


# -- Current Condition eligibility ---------------------------------------------


def test_current_condition_statuses_exclude_draft():
    assert CURRENT_CONDITION_STATUSES == frozenset({"SUBMITTED", "FINALIZED"})
    assert "DRAFT" in ELIGIBLE_STATUSES  # legacy set unchanged until R1B


def test_newer_draft_does_not_displace_finalized():
    readings = [_reading("FIN", "2026-01-10", de=False, nde=False), _reading("DRAFT", "2026-02-10", de=True, status="DRAFT")]
    assert select_current_condition_cm(readings)["condition_monitoring_reading_code"] == "FIN"
    assert current_leak_condition(readings)["active"] is False
    # Intentional domain change: the legacy selector still picks the DRAFT.
    assert select_latest_valid_cm(readings)["condition_monitoring_reading_code"] == "DRAFT"


def test_newer_submitted_is_current():
    readings = [_reading("FIN", "2026-01-10", de=False, nde=False), _reading("SUB", "2026-02-10", de=True, status="SUBMITTED")]
    assert select_current_condition_cm(readings)["condition_monitoring_reading_code"] == "SUB"
    assert current_leak_condition(readings)["state"] == "LEAK_DE"


@pytest.mark.parametrize("status", ["RETURNED_FOR_CORRECTION", "DRAFT", None, ""])
def test_other_workflow_statuses_are_not_current(status):
    assert is_current_condition_candidate(_reading("X", "2026-02-10", de=True, status=status)) is False


def test_deleted_newer_row_is_excluded():
    readings = [_reading("OLD", "2026-01-10", de=False, nde=False), _reading("DEL", "2026-02-10", de=True, deleted_at="2026-02-11T00:00:00")]
    assert select_current_condition_cm(readings)["condition_monitoring_reading_code"] == "OLD"


def test_newer_row_without_observation_is_excluded():
    empty = _reading("EMPTY", "2026-02-10", suction_temp=None)
    readings = [_reading("OLD", "2026-01-10", de=True), empty]
    assert select_current_condition_cm(readings)["condition_monitoring_reading_code"] == "OLD"


@pytest.mark.parametrize("bad_date", [None, "", "not-a-date"])
def test_rows_without_a_usable_reading_date_are_excluded(bad_date):
    readings = [_reading("OLD", "2026-01-10", de=False, nde=False), _reading("NODATE", bad_date, de=True)]
    assert select_current_condition_cm(readings)["condition_monitoring_reading_code"] == "OLD"


def test_row_without_asset_code_is_excluded():
    readings = [_reading("OLD", "2026-01-10"), _reading("NOASSET", "2026-02-10", asset_code=None)]
    assert select_current_condition_cm(readings)["condition_monitoring_reading_code"] == "OLD"


# -- ordering / tie-break ------------------------------------------------------


def test_same_reading_date_breaks_on_created_at():
    readings = [
        _reading("LATE", "2026-02-10", created_at="2026-02-10T09:00:00Z"),
        _reading("EARLY", "2026-02-10", created_at="2026-02-10T08:00:00Z"),
    ]
    assert select_current_condition_cm(readings)["condition_monitoring_reading_code"] == "LATE"


def test_same_reading_date_and_created_at_breaks_on_reading_code():
    readings = [_reading("CMONR-A", "2026-02-10"), _reading("CMONR-B", "2026-02-10")]
    assert select_current_condition_cm(readings)["condition_monitoring_reading_code"] == "CMONR-B"
    assert select_current_condition_cm(list(reversed(readings)))["condition_monitoring_reading_code"] == "CMONR-B"


def test_mixed_timestamp_representations_order_by_time_not_text():
    # Same reading date in two text forms. As text, "...T..." sorts after "... ..."
    # (so a text compare would pick ISO-Z); by time TEXT-SPACE was created later.
    readings = [
        _reading("TEXT-SPACE", "2026-02-10 00:00:00", created_at="2026-02-10 09:00:00"),
        _reading("ISO-Z", "2026-02-10T00:00:00Z", created_at="2026-02-10T08:00:00Z"),
        _reading("DATE-OBJ", date(2026, 2, 9), created_at=datetime(2026, 2, 10, 12, 0)),
    ]
    assert select_current_condition_cm(readings)["condition_monitoring_reading_code"] == "TEXT-SPACE"


def test_timezone_offsets_are_normalised():
    readings = [
        _reading("PLUS7", "2026-02-10", created_at="2026-02-10T15:00:00+07:00"),  # 08:00 UTC
        _reading("UTC", "2026-02-10", created_at="2026-02-10T09:00:00Z"),
    ]
    assert select_current_condition_cm(readings)["condition_monitoring_reading_code"] == "UTC"


# -- provenance never affects selection ----------------------------------------


@pytest.mark.parametrize("newer_provenance", ["HISTORICAL_IMPORT", "MANUAL", "WHATSAPP"])
def test_provenance_has_no_selection_priority(newer_provenance):
    older = _reading("OLDER", "2026-07-01", de=False, nde=False, provenance="MANUAL")
    newer = _reading("NEWER", "2026-07-02", de=True, provenance=newer_provenance)
    assert select_current_condition_cm([older, newer])["condition_monitoring_reading_code"] == "NEWER"
    assert select_current_condition_cm([newer, older])["condition_monitoring_reading_code"] == "NEWER"


def test_older_historical_import_does_not_become_current():
    batch_a = _reading(
        "LTSA-CMONR-HISTPDF-0000000000000001", "2026-06-29", de=True, provenance="HISTORICAL_IMPORT",
        source_reference="ltsa_hist_cm_pdf:0123456789abcdef:p1:r1", created_at="2026-09-24T14:10:00Z",
    )
    live = _reading("CMONR-LIVE", "2026-08-13", de=False, nde=False, created_at="2026-08-13T02:00:00Z")
    current = current_leak_condition([batch_a, live])
    assert current["reading_code"] == "CMONR-LIVE" and current["active"] is False


# -- compatibility of existing surfaces ----------------------------------------


def test_evaluate_current_condition_keeps_its_schema_and_adds_canonical_state():
    result = evaluate_current_condition(_reading("A", "2026-02-10", de=True, nde=True))
    assert result["leak"]["status"] == "LEAK_DE_NDE"
    assert result["leak"]["state"] == "LEAK_DE_AND_NDE" and result["leak"]["active"] is True


def test_recent_leak_observed_window_rule_is_unchanged():
    today = date(2026, 9, 24)
    readings = [
        {"reading_date": (today - timedelta(days=10)).isoformat(), "mechanical_seal_leak_de": True},
        {"reading_date": (today - timedelta(days=2)).isoformat(), "mechanical_seal_leak_de": False, "mechanical_seal_leak_nde": False},
    ]
    # "Was a leak observed in the last 30 days?" -> yes, although Current Condition is NO_LEAK.
    assert mis.leak_flag_from_readings(readings, today=today)["flagged"] is True
    assert mis.leak_flag_from_readings(readings[1:], today=today)["flagged"] is False
    assert mis.DEFAULT_CONDITION_MONITORING_WINDOW_DAYS == 30
