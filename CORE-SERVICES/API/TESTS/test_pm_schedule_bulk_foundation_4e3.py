"""AI5R-PHASE4E3 -- PM Bulk Schedule Table, backend atomic bulk-create.

Covers Section I (one atomic bulk endpoint, server-generated PMSCH-* per
row, all-or-nothing, zero pm_occurrence), Section J (within-batch
duplicate rejection keyed by asset_code+frequency+effective_date), and
Section M (a batch with any invalid row creates NOTHING; a corrected
retry creates exactly the expected rows with fresh, non-duplicate codes).

Same FakeRunner discipline as test_pm_schedule_foundation_4e1.py /
test_schedule_creation_never_creates_actual.py.
"""

import json
import re
import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.operational_registry_repository import (  # noqa: E402
    BulkPMScheduleValidationError,
    PMScheduleRepository,
)

PMSCH_RE = re.compile(r"PMSCH-[0-9A-F]{12}")


class FakeRunner:
    """query_scalar call order for a valid bulk_create(): [0] canonical-
    pump SELECT, [1..N] one collision-check SELECT per generated code
    (N == number of rows, absent collisions), [N+1] the final bulk
    INSERT. `pump_response` controls which asset_codes look canonical;
    every collision-check reports "not taken" unless `collide_first` is
    set (used by the retry test)."""

    def __init__(self, canonical_tags: list[str], collide_first: bool = False):
        self.scalar_calls: list[str] = []
        self._canonical_tags = canonical_tags
        self._collide_first = collide_first
        self._collision_used = False

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        if "SELECT tag_number FROM public.ltsa_pumps" in sql:
            return json.dumps([{"tag_number": tag} for tag in self._canonical_tags])
        if "SELECT 1 AS present FROM public.pm_schedule" in sql:
            if self._collide_first and not self._collision_used:
                self._collision_used = True
                return json.dumps([{"present": 1}])
            return "[]"
        if "INSERT INTO public.pm_schedule" in sql:
            codes = PMSCH_RE.findall(sql)
            return json.dumps([{"pm_schedule_code": code} for code in codes])
        return "[]"


def _row(client_row_id, asset_code="211-P-1A", frequency="MONTHLY", effective_date="2026-10-01", **overrides):
    row = {
        "client_row_id": client_row_id,
        "asset_code": asset_code,
        "asset_type": None,
        "procedure": None,
        "frequency": frequency,
        "trigger_type": "CALENDAR",
        "interval_unit": None,
        "effective_date": effective_date,
        "next_due": effective_date,
        "assigned_to": None,
        "estimated_duration_hours": None,
        "provenance": "MANUAL",
        "source_reference": None,
        "planned_activities": None,
    }
    row.update(overrides)
    return row


def test_bulk_create_empty_rows_is_a_no_op():
    runner = FakeRunner(canonical_tags=[])
    assert PMScheduleRepository(runner).bulk_create(rows=[], actor="actor-1") == []
    assert runner.scalar_calls == []


def test_bulk_create_issues_exactly_one_insert_statement_for_n_rows_never_touching_pm_occurrence():
    rows = [
        _row("row-1", asset_code="211-P-1A"),
        _row("row-2", asset_code="211-P-1B"),
        _row("row-3", asset_code="211-P-1C"),
    ]
    runner = FakeRunner(canonical_tags=["211-P-1A", "211-P-1B", "211-P-1C"])

    result = PMScheduleRepository(runner).bulk_create(rows=rows, actor="actor-1")

    assert len(result) == 3
    assert {r["client_row_id"] for r in result} == {"row-1", "row-2", "row-3"}
    for r in result:
        assert PMSCH_RE.fullmatch(r["pm_schedule_code"])
    codes = [r["pm_schedule_code"] for r in result]
    assert len(set(codes)) == 3  # all distinct

    insert_calls = [sql for sql in runner.scalar_calls if "INSERT INTO public.pm_schedule" in sql]
    assert len(insert_calls) == 1
    for sql in runner.scalar_calls:
        assert "INSERT INTO pm_occurrence" not in sql
    assert "audit" in insert_calls[0]  # CREATE audit trail wired through, same as single-create


def test_bulk_create_rejects_unknown_pump_and_creates_nothing():
    rows = [_row("row-1", asset_code="211-P-1A"), _row("row-2", asset_code="UNKNOWN-9")]
    runner = FakeRunner(canonical_tags=["211-P-1A"])  # UNKNOWN-9 does not exist

    with pytest.raises(BulkPMScheduleValidationError) as excinfo:
        PMScheduleRepository(runner).bulk_create(rows=rows, actor="actor-1")

    assert "row-2" in excinfo.value.row_errors
    assert "UNKNOWN-9" in excinfo.value.row_errors["row-2"]
    assert not any("INSERT INTO public.pm_schedule" in sql for sql in runner.scalar_calls)


def test_bulk_create_rejects_within_batch_duplicate_asset_frequency_date_and_creates_nothing():
    rows = [
        _row("row-1", asset_code="211-P-1A", frequency="MONTHLY", effective_date="2026-10-01"),
        _row("row-2", asset_code="211-P-1A", frequency="MONTHLY", effective_date="2026-10-01"),
    ]
    runner = FakeRunner(canonical_tags=["211-P-1A"])

    with pytest.raises(BulkPMScheduleValidationError) as excinfo:
        PMScheduleRepository(runner).bulk_create(rows=rows, actor="actor-1")

    assert "row-2" in excinfo.value.row_errors
    assert "Duplicate" in excinfo.value.row_errors["row-2"]
    assert not any("INSERT INTO public.pm_schedule" in sql for sql in runner.scalar_calls)


def test_bulk_create_allows_same_pump_with_different_frequency_or_date():
    rows = [
        _row("row-1", asset_code="211-P-1A", frequency="MONTHLY", effective_date="2026-10-01"),
        _row("row-2", asset_code="211-P-1A", frequency="WEEKLY", effective_date="2026-10-01"),
        _row("row-3", asset_code="211-P-1A", frequency="MONTHLY", effective_date="2026-11-01"),
    ]
    runner = FakeRunner(canonical_tags=["211-P-1A"])

    result = PMScheduleRepository(runner).bulk_create(rows=rows, actor="actor-1")
    assert len(result) == 3


def test_bulk_create_nine_valid_one_invalid_creates_zero_then_retry_creates_exactly_ten_with_no_duplicate_codes():
    # Section M's own rollback scenario.
    valid_rows = [_row(f"row-{i}", asset_code=f"211-P-{i}", effective_date="2026-10-01") for i in range(9)]
    bad_batch = valid_rows + [_row("row-bad", asset_code="NOT-REAL")]
    runner = FakeRunner(canonical_tags=[f"211-P-{i}" for i in range(9)])

    with pytest.raises(BulkPMScheduleValidationError):
        PMScheduleRepository(runner).bulk_create(rows=bad_batch, actor="actor-1")
    assert not any("INSERT INTO public.pm_schedule" in sql for sql in runner.scalar_calls)

    corrected_batch = valid_rows + [_row("row-9", asset_code="211-P-9", effective_date="2026-10-01")]
    runner2 = FakeRunner(canonical_tags=[f"211-P-{i}" for i in range(10)])
    result = PMScheduleRepository(runner2).bulk_create(rows=corrected_batch, actor="actor-1")

    assert len(result) == 10
    codes = [r["pm_schedule_code"] for r in result]
    assert len(set(codes)) == 10  # no duplicate PMSCH codes


def test_bulk_create_retries_a_colliding_generated_code():
    rows = [_row("row-1")]
    runner = FakeRunner(canonical_tags=["211-P-1A"], collide_first=True)

    result = PMScheduleRepository(runner).bulk_create(rows=rows, actor="actor-1")

    assert len(result) == 1
    collision_checks = [sql for sql in runner.scalar_calls if "SELECT 1 AS present" in sql]
    assert len(collision_checks) == 2  # first candidate rejected, second accepted


def test_bulk_create_planned_activities_are_jsonb_with_no_done_field_and_no_legacy_numeric_code():
    rows = [
        _row(
            "row-1",
            planned_activities=[{"family": "Flushing Line", "variant": "DE", "code": "FLUSHING_LINE_DE"}],
        )
    ]
    runner = FakeRunner(canonical_tags=["211-P-1A"])

    PMScheduleRepository(runner).bulk_create(rows=rows, actor="actor-1")

    insert_sql = next(sql for sql in runner.scalar_calls if "INSERT INTO public.pm_schedule" in sql)
    assert "::jsonb" in insert_sql
    assert "FLUSHING_LINE_DE" in insert_sql
    assert '"done"' not in insert_sql
