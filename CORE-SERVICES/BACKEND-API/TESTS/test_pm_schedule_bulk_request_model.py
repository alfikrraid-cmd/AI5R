"""AI5R-PHASE4E3 -- PMScheduleBulkRow/PMScheduleBulkCreateRequest: the
Section G ERROR classifications that are enforceable at the request-model
layer (frequency, start date, duration, planned-activity codes), plus
row-correlation via client_row_id."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from models.requests import PMScheduleBulkCreateRequest, PMScheduleBulkRow  # noqa: E402


def _row(**overrides):
    values = {
        "client_row_id": "row-1",
        "asset_code": "211-P-1A",
        "frequency": "MONTHLY",
        "trigger_type": "CALENDAR",
        "effective_date": "2026-10-01",
    }
    values.update(overrides)
    return values


def test_valid_row_round_trips():
    row = PMScheduleBulkRow(**_row())
    assert row.client_row_id == "row-1"
    assert row.asset_code == "211-P-1A"


def test_rejects_missing_asset_code():
    with pytest.raises(ValidationError):
        PMScheduleBulkRow(**_row(asset_code=""))


def test_rejects_unsupported_frequency():
    with pytest.raises(ValidationError):
        PMScheduleBulkRow(**_row(frequency="YEARLY"))


def test_accepts_every_supported_frequency():
    for frequency in ("DAILY", "WEEKLY", "MONTHLY", "RUNTIME_BASED"):
        assert PMScheduleBulkRow(**_row(frequency=frequency)).frequency == frequency


def test_rejects_missing_start_date():
    with pytest.raises(ValidationError):
        PMScheduleBulkRow(**_row(effective_date=""))


def test_rejects_negative_duration():
    with pytest.raises(ValidationError):
        PMScheduleBulkRow(**_row(estimated_duration_hours=-1))


def test_accepts_zero_duration():
    assert PMScheduleBulkRow(**_row(estimated_duration_hours=0)).estimated_duration_hours == 0


def test_rejects_a_done_field_in_planned_activities():
    with pytest.raises(ValidationError):
        PMScheduleBulkRow(**_row(planned_activities=[{"code": "RESERVOIR", "done": True}]))


def test_rejects_unknown_planned_activity_code():
    with pytest.raises(ValidationError):
        PMScheduleBulkRow(**_row(planned_activities=[{"code": "RESERVOIR_DE"}]))  # no such code exists


def test_normalizes_planned_activities_from_code_alone():
    row = PMScheduleBulkRow(**_row(planned_activities=[{"code": "FLUSHING_LINE_DE"}]))
    assert row.planned_activities == [{"family": "Flushing Line", "variant": "DE", "code": "FLUSHING_LINE_DE"}]


def test_bulk_request_rejects_empty_rows():
    with pytest.raises(ValidationError):
        PMScheduleBulkCreateRequest(rows=[])


def test_bulk_request_accepts_multiple_rows_and_preserves_order():
    request = PMScheduleBulkCreateRequest(rows=[_row(client_row_id="row-a"), _row(client_row_id="row-b", asset_code="211-P-1B")])
    assert [row.client_row_id for row in request.rows] == ["row-a", "row-b"]
