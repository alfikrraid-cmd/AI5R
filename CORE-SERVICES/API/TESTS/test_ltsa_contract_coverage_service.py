"""MWO-LTSA-CONTRACT-SCOPE-R3 -- fast, no-DB unit tests for
ltsa_contract_coverage_service.py's pure helper functions. Real-DB
behavior (period overlap, monitoring counts, RBAC scope, constraints) is
covered by test_ltsa_contract_scope_real_db.py -- these tests only cover
what's genuinely computable without a database.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_CORE_SERVICES_DIR = Path(__file__).resolve().parents[2]
if str(_CORE_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_SERVICES_DIR))

from API.ltsa_contract_coverage_service import (  # noqa: E402
    InvalidReportingPeriod,
    _coverage_percent,
    _ma_bucket,
    _validate_period,
)


@pytest.mark.parametrize(
    "area,expected",
    [
        ("HOC", "MA1"),
        ("HSC", "MA2"),
        ("HCC", "MA2"),
        ("SPK", "MA2"),
        ("S_PAKNING", "MA2"),
        ("UTL", "MA3"),
        ("UTILITIES", "MA3"),
        ("OM", "MA4"),
        ("OIL MOVEMENT", "MA4"),
        ("FRAKSINASI", "UNMAPPED"),
        ("REAKTOR", "UNMAPPED"),
        (None, "UNMAPPED"),
        ("", "UNMAPPED"),
    ],
)
def test_ma_bucket_uses_canonical_mapping(area, expected):
    assert _ma_bucket(area) == expected


def test_validate_period_accepts_start_before_end():
    _validate_period("2026-01-01", "2026-01-31")  # no raise


def test_validate_period_accepts_equal_start_and_end():
    _validate_period("2026-01-01", "2026-01-01")  # single-day period, no raise


def test_validate_period_rejects_start_after_end():
    with pytest.raises(InvalidReportingPeriod):
        _validate_period("2026-02-01", "2026-01-01")


def test_validate_period_rejects_malformed_dates():
    with pytest.raises(InvalidReportingPeriod):
        _validate_period("not-a-date", "2026-01-01")


def test_coverage_percent_null_when_denominator_zero():
    assert _coverage_percent(0, 0) == None  # noqa: E711 -- explicit None, not falsy-0


def test_coverage_percent_computed_normally():
    assert _coverage_percent(1, 4) == 25.0
