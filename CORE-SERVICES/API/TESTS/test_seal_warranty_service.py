"""MECHANICAL-SEAL-DOMAIN-CONSOLIDATION-R1 -- Part E tests for the new,
today-relative EXPIRING SOON / time_status calculation and the proactive
seal-unit warranty overview, on top of seal_warranty_service.py's
existing, unmodified window_status/decision_status machinery.

Same FakeRunner discipline as test_seal_unit_repository.py, extended to a
queue so build_seal_unit_warranty_overview's two sequential reads
(SealUnitRepository.find_by_id, then SealLifecycleEventRepository.
list_by_seal_unit) each get their own canned response.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

import pytest  # noqa: E402

from API.seal_warranty_service import (  # noqa: E402
    EXPIRING_SOON_DAYS,
    WARRANTY_MONTHS,
    WARRANTY_ELIGIBILITY_NOTE,
    SealUnitNotFoundError,
    build_seal_unit_warranty_overview,
    calculate_time_status,
)


class QueueFakeRunner:
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.scalar_calls: list[str] = []

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        return self.responses.pop(0)


# --- calculate_time_status: pure, no DB access ---


def test_within_warranty_period_far_from_expiry():
    installation_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    now = datetime(2026, 3, 1, tzinfo=timezone.utc)  # warranty_end = 2027-07-01
    result = calculate_time_status(installation_date, now=now)
    assert result.time_status == "WITHIN_WARRANTY_PERIOD"
    assert result.days_remaining > EXPIRING_SOON_DAYS


def test_exactly_expiring_soon_days_remaining_is_expiring_soon():
    # installation_date + 18 calendar months = 2027-01-01; `now` set to
    # that same date puts days_remaining at 0, well inside the mission's
    # own "<=90 days remaining" EXPIRING SOON boundary.
    installation_date = datetime(2025, 7, 1, tzinfo=timezone.utc)
    now = datetime(2027, 1, 1, tzinfo=timezone.utc)
    result = calculate_time_status(installation_date, now=now)
    assert result.warranty_end == datetime(2027, 1, 1, tzinfo=timezone.utc)
    assert result.days_remaining == 0
    assert result.time_status == "EXPIRING_SOON"


def test_ninety_one_days_remaining_is_still_within_warranty_period():
    installation_date = datetime(2025, 7, 1, tzinfo=timezone.utc)  # warranty_end = 2027-01-01
    now = datetime(2026, 10, 2, tzinfo=timezone.utc)  # 91 days before warranty_end
    result = calculate_time_status(installation_date, now=now)
    assert result.days_remaining == 91
    assert result.time_status == "WITHIN_WARRANTY_PERIOD"


def test_eighty_nine_days_remaining_is_expiring_soon():
    # RELEASE-READINESS-GATE -- explicit 89-day case (one day inside the
    # <=90 boundary), distinct from the exactly-90 and exactly-91 cases
    # above.
    installation_date = datetime(2025, 7, 1, tzinfo=timezone.utc)  # warranty_end = 2027-01-01
    now = datetime(2026, 10, 4, tzinfo=timezone.utc)  # 89 days before warranty_end
    result = calculate_time_status(installation_date, now=now)
    assert result.days_remaining == 89
    assert result.time_status == "EXPIRING_SOON"


def test_month_end_clamps_into_a_leap_year_february():
    # RELEASE-READINESS-GATE -- month-end + leap-year calendar-month
    # arithmetic: 2026-08-31 + 18 calendar months lands on a February
    # that only has 29 days in a leap year (2028 is divisible by 4, not
    # by 100) -- day must clamp to 29, never overflow into March.
    installation_date = datetime(2026, 8, 31, tzinfo=timezone.utc)
    now = installation_date
    result = calculate_time_status(installation_date, now=now)
    assert result.warranty_end == datetime(2028, 2, 29, tzinfo=timezone.utc)


def test_month_end_clamps_into_a_non_leap_year_february():
    # Same clamp, but landing on a February in a non-leap year (2027) --
    # must clamp to 28, not 29 or an overflowed March 2/3.
    installation_date = datetime(2025, 8, 31, tzinfo=timezone.utc)
    now = installation_date
    result = calculate_time_status(installation_date, now=now)
    assert result.warranty_end == datetime(2027, 2, 28, tzinfo=timezone.utc)


def test_exactly_on_warranty_end_is_still_within_not_ended():
    installation_date = datetime(2025, 7, 1, tzinfo=timezone.utc)
    now = datetime(2027, 1, 1, tzinfo=timezone.utc)  # exactly warranty_end
    result = calculate_time_status(installation_date, now=now)
    assert result.time_status in ("EXPIRING_SOON", "WITHIN_WARRANTY_PERIOD")
    assert result.time_status != "WARRANTY_PERIOD_ENDED"


def test_one_day_past_warranty_end_is_ended():
    installation_date = datetime(2025, 7, 1, tzinfo=timezone.utc)
    now = datetime(2027, 1, 2, tzinfo=timezone.utc)  # one day after warranty_end
    result = calculate_time_status(installation_date, now=now)
    assert result.time_status == "WARRANTY_PERIOD_ENDED"
    assert result.days_remaining < 0


def test_warranty_months_constant_is_eighteen_and_unchanged():
    assert WARRANTY_MONTHS == 18


def test_expiring_soon_threshold_is_ninety_days():
    assert EXPIRING_SOON_DAYS == 90


# --- build_seal_unit_warranty_overview: never fabricates, never auto-approves ---


def test_overview_raises_when_seal_unit_does_not_exist():
    runner = QueueFakeRunner(["[]"])  # find_by_id -> no rows
    with pytest.raises(SealUnitNotFoundError):
        build_seal_unit_warranty_overview(runner, "missing-unit")


def test_overview_is_na_when_not_currently_installed_never_fabricated():
    unit = {"seal_unit_id": "11111111-1111-4111-8111-111111111111", "seal_code": "SC-1", "current_pump_tag_number": None}
    runner = QueueFakeRunner([json.dumps([unit])])
    overview = build_seal_unit_warranty_overview(runner, "11111111-1111-4111-8111-111111111111")
    assert overview["time_status"] == "N/A"
    assert overview["installation_date"] is None
    assert overview["warranty_end"] is None
    assert overview["days_remaining"] is None
    # Only one query issued -- current_pump_tag_number is None short-circuits
    # before ever looking up lifecycle events (never guesses one).
    assert len(runner.scalar_calls) == 1


def test_overview_is_na_when_current_pump_set_but_no_matching_install_event():
    unit = {"seal_unit_id": "11111111-1111-4111-8111-111111111111", "seal_code": "SC-1", "current_pump_tag_number": "110-P-8A"}
    events: list[dict] = []  # no INSTALL event at all -- ambiguous, must not guess
    runner = QueueFakeRunner([json.dumps([unit]), json.dumps(events)])
    overview = build_seal_unit_warranty_overview(runner, "11111111-1111-4111-8111-111111111111")
    assert overview["time_status"] == "N/A"
    assert overview["installation_date"] is None


def test_overview_uses_the_most_recent_install_event_on_the_current_pump():
    unit = {"seal_unit_id": "11111111-1111-4111-8111-111111111111", "seal_code": "SC-1", "current_pump_tag_number": "110-P-8A"}
    events = [
        # Earlier INSTALL on a DIFFERENT pump -- must be ignored.
        {"event_type": "INSTALL", "pump_tag_number": "999-P-1A", "event_at": "2020-01-01T00:00:00+00:00"},
        # Earlier INSTALL on the current pump, later REMOVE, then a
        # second, more recent INSTALL back onto the same pump -- the
        # overview must use the LATEST one, never the first.
        {"event_type": "INSTALL", "pump_tag_number": "110-P-8A", "event_at": "2024-01-01T00:00:00+00:00"},
        {"event_type": "REMOVE", "pump_tag_number": "110-P-8A", "event_at": "2024-06-01T00:00:00+00:00"},
        {"event_type": "INSTALL", "pump_tag_number": "110-P-8A", "event_at": "2026-01-01T00:00:00+00:00"},
    ]
    runner = QueueFakeRunner([json.dumps([unit]), json.dumps(events)])
    now = datetime(2026, 3, 1, tzinfo=timezone.utc)
    overview = build_seal_unit_warranty_overview(runner, "11111111-1111-4111-8111-111111111111", now=now)
    assert overview["installation_date"].startswith("2026-01-01")
    assert overview["time_status"] == "WITHIN_WARRANTY_PERIOD"
    assert overview["warranty_period_months"] == WARRANTY_MONTHS
    assert overview["expiring_soon_days"] == EXPIRING_SOON_DAYS


def test_overview_never_states_a_claim_decision_only_a_time_status_and_note():
    # Part E's own rule: time eligibility and contractual eligibility are
    # different -- the overview must carry the fixed eligibility note and
    # must never contain an ACCEPTED/REJECTED-style decision field.
    unit = {"seal_unit_id": "11111111-1111-4111-8111-111111111111", "seal_code": "SC-1", "current_pump_tag_number": "110-P-8A"}
    events = [{"event_type": "INSTALL", "pump_tag_number": "110-P-8A", "event_at": "2026-01-01T00:00:00+00:00"}]
    runner = QueueFakeRunner([json.dumps([unit]), json.dumps(events)])
    overview = build_seal_unit_warranty_overview(runner, "11111111-1111-4111-8111-111111111111", now=datetime(2026, 2, 1, tzinfo=timezone.utc))
    assert overview["eligibility_note"] == WARRANTY_ELIGIBILITY_NOTE
    assert "decision" not in overview
    assert "decision_status" not in overview
