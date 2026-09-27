"""LTSA_INSTALLATION_BASED_MTBF_R1 -- MTBF (Installation-based · Calendar
time) from completed installation intervals. Rows mirror the production
installation_report rows; nothing depends on the wall clock."""

import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

import pytest

from API.installation_interval_contract import (
    COMPARABLE,
    EXCLUDED_SAME_DAY,
    IDENTITY_CHANGED,
    IDENTITY_CONFIRMED_SAME,
    IDENTITY_UNKNOWN,
    NON_COMPARABLE,
    installation_based_mtbf,
)
from API.TESTS.test_current_installation import NOW, PRODUCTION_ROWS, report, service_for


def mtbf(rows, tag):
    return installation_based_mtbf(rows, tag)


# A. 945-P-9B-like pair
def test_a_same_seal_pair_gives_20_days_480_hours_confirmed_same():
    result = mtbf(PRODUCTION_ROWS, "945-P-9B")
    assert result.completed_interval_count == 1
    (interval,) = result.intervals
    assert (interval.previous_installation_code, interval.previous_installation_date) == ("INSTL-022-2026", "2026-04-17")
    assert (interval.next_installation_code, interval.next_installation_date) == ("INSTL-026-2026", "2026-05-07")
    assert (interval.mtbf_days, interval.mtbf_hours) == (20, 480)
    assert (interval.previous_seal_type, interval.previous_seal_size) == ("T48MP", '2.3/8"')
    assert (interval.next_seal_type, interval.next_seal_size) == ("T48MP", '2.3/8"')
    assert interval.seal_identity_status == IDENTITY_CONFIRMED_SAME
    assert interval.comparability_status == COMPARABLE
    assert (interval.position, interval.time_basis, interval.precision) == ("PUMP_LEVEL", "CALENDAR_TIME", "DATE_ONLY")
    assert (result.installation_based_mtbf_days, result.installation_based_mtbf_hours) == (20, 480)


# B. missing type/size keeps the interval, identity UNKNOWN
@pytest.mark.parametrize("pump, days", [("220-P-3A", 64), ("200-P-4B", 56)])
def test_b_missing_type_and_size_interval_stays_valid_with_unknown_identity(pump, days):
    rows = PRODUCTION_ROWS + [
        report("INSTL-023-2026", "200-P-4B", "200-P-4B", "2026-04-09"),
        report("INSTL-040-2026", "200-P-4B", "200-P-4B", "2026-06-04"),
    ]
    result = mtbf(rows, pump)
    (interval,) = result.intervals
    assert (interval.mtbf_days, interval.mtbf_hours) == (days, days * 24)
    assert interval.seal_identity_status == IDENTITY_UNKNOWN
    assert interval.comparability_status == COMPARABLE


def test_identity_changed_when_a_recorded_type_or_size_differs():
    type_change = [report("I-1", "P", "P-X", "2026-01-01", "T48MP"), report("I-2", "P", "P-X", "2026-02-01", "T48LP")]
    size_change = [report("I-1", "P", "P-X", "2026-01-01", "T48MP", seal_size='2.1/8"'),
                   report("I-2", "P", "P-X", "2026-02-01", "T48MP", seal_size='2.3/8"')]
    one_size_missing = [report("I-1", "P", "P-X", "2026-01-01", "T48MP", seal_size='2.1/8"'),
                        report("I-2", "P", "P-X", "2026-02-01", "T48MP")]
    assert mtbf(type_change, "P-X").intervals[0].seal_identity_status == IDENTITY_CHANGED
    assert mtbf(size_change, "P-X").intervals[0].seal_identity_status == IDENTITY_CHANGED
    assert mtbf(one_size_missing, "P-X").intervals[0].seal_identity_status == IDENTITY_UNKNOWN


# C / D. DE->DE and NDE->NDE are comparable
@pytest.mark.parametrize("position", ["DE", "NDE"])
def test_cd_same_structured_position_is_comparable(position):
    rows = [report("I-1", "P", "P-POS", "2026-01-01", "T8B1", seal_location=position),
            report("I-2", "P", "P-POS", "2026-03-02", "T8B1", seal_location=position.lower())]
    result = mtbf(rows, "P-POS")
    assert result.completed_interval_count == 1
    assert result.intervals[0].position == position
    assert result.intervals[0].mtbf_days == 60


# E / F. mixed positions are never compared
@pytest.mark.parametrize("first, second", [("DE", "NDE"), (None, "DE"), ("NDE", None)])
def test_ef_mixed_positions_are_non_comparable(first, second):
    rows = [report("I-1", "P", "P-MIX", "2026-01-01", "T8B1", seal_location=first),
            report("I-2", "P", "P-MIX", "2026-03-02", "T8B1", seal_location=second)]
    result = mtbf(rows, "P-MIX")
    assert result.completed_interval_count == 0
    assert result.installation_based_mtbf_days is None
    (transition,) = result.non_comparable_transitions
    assert transition.comparability_status == NON_COMPARABLE
    assert "->" in transition.position


def test_positions_are_never_inferred_from_file_names():
    rows = [report("I-1", "P", "P-FN", "2026-01-01", "T8B1", source_document_name="SCAN (DE).pdf"),
            report("I-2", "P", "P-FN", "2026-02-01", "T8B1", seal_location="DE")]
    assert mtbf(rows, "P-FN").completed_interval_count == 0


def test_interleaved_positions_pair_within_each_position():
    rows = [report("I-1", "P", "P-IL", "2026-01-01", "A", seal_location="DE"),
            report("I-2", "P", "P-IL", "2026-02-01", "B", seal_location="NDE"),
            report("I-3", "P", "P-IL", "2026-03-01", "A", seal_location="DE")]
    result = mtbf(rows, "P-IL")
    assert [(i.position, i.mtbf_days) for i in result.intervals] == [("DE", 59)]
    assert len(result.non_comparable_transitions) == 2


# G / H. single installation or none: no MTBF
def test_g_single_installation_has_no_completed_interval():
    result = mtbf(PRODUCTION_ROWS, "211-P-1A")
    assert (result.installation_event_count, result.completed_interval_count) == (1, 0)
    assert result.installation_based_mtbf_days is None and result.installation_based_mtbf_hours is None
    assert result.precision is None


def test_h_no_installation_has_no_mtbf():
    result = mtbf(PRODUCTION_ROWS, "701-P-1A")
    assert (result.installation_event_count, result.completed_interval_count) == (0, 0)
    assert result.installation_based_mtbf_days is None and result.intervals == ()


# I. current service age is not part of MTBF
def test_i_current_service_age_is_excluded_from_mtbf():
    service = service_for("945-P-9B")
    current = service.build_current_installation("945-P-9B", now=NOW).current
    result = service.build_installation_based_mtbf("945-P-9B")
    assert current.time_since_installation_days == 141  # latest installation -> 2026-09-25
    assert result.installation_based_mtbf_days == 20     # completed interval only
    assert all(i.next_installation_code != "TODAY" for i in result.intervals)


# J. mean of completed comparable intervals only
def test_j_pump_mean_uses_only_completed_comparable_intervals():
    rows = [report("I-1", "P", "P-J", "2026-01-01", "T48MP"),
            report("I-2", "P", "P-J", "2026-01-21", "T48MP"),  # 20 d
            report("I-3", "P", "P-J", "2026-03-02", "T48MP"),  # 40 d
            report("I-4", "P", "P-J", "2026-03-02", "T48MP"),  # same day: excluded
            report("I-5", "P", "P-J", "2026-02-01", "T8B1", seal_location="DE")]  # other position
    result = mtbf(rows, "P-J")
    assert [i.mtbf_days for i in result.intervals] == [20, 40]
    assert (result.completed_interval_count, result.installation_based_mtbf_days, result.installation_based_mtbf_hours) == (2, 30, 720)


def test_mean_keeps_a_fractional_value():
    rows = [report("I-1", "P", "P-F", "2026-01-01"), report("I-2", "P", "P-F", "2026-01-21"), report("I-3", "P", "P-F", "2026-02-11")]
    assert mtbf(rows, "P-F").installation_based_mtbf_days == 20.5


# K. same-day pair is never a 0-day MTBF
def test_k_same_day_pair_is_excluded_not_zero():
    rows = [report("I-1", "P", "P-K", "2026-05-05", "T48LP"), report("I-2", "P", "P-K", "2026-05-05", "T48LP")]
    result = mtbf(rows, "P-K")
    assert result.completed_interval_count == 0
    assert result.installation_based_mtbf_days is None
    (excluded,) = result.excluded_intervals
    assert excluded.comparability_status == EXCLUDED_SAME_DAY


# L. report_date drives ordering; installation_code only breaks ties
def test_l_ordering_by_date_not_installation_code():
    # Production numbering is not chronological (INSTL-019 is 03-30, INSTL-020 is 03-16).
    rows = [report("INSTL-019-2026", "P", "P-L", "2026-03-30", "A"),
            report("INSTL-020-2026", "P", "P-L", "2026-03-16", "A")]
    (interval,) = mtbf(rows, "P-L").intervals
    assert (interval.previous_installation_code, interval.next_installation_code) == ("INSTL-020-2026", "INSTL-019-2026")
    assert interval.mtbf_days == 14


def test_timestamp_evidence_uses_exact_hours():
    rows = [report("I-1", "P", "P-TS", "2026-09-01T08:00:00+07:00", "A"),
            report("I-2", "P", "P-TS", "2026-09-03T20:00:00+07:00", "A")]
    (interval,) = mtbf(rows, "P-TS").intervals
    assert (interval.mtbf_days, interval.mtbf_hours, interval.precision) == (2, 60, "TIMESTAMP")


def test_other_pumps_and_attribution_follow_the_current_installation_contract():
    # INSTL-041 is 140-P-26B's report despite plant_equip_no 140-P-26A.
    assert mtbf(PRODUCTION_ROWS, "140-P-26A").completed_interval_count == 0
    assert mtbf(PRODUCTION_ROWS, "140-P-26B").completed_interval_count == 0
