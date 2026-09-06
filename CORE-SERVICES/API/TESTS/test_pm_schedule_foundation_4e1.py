"""AI5R-PHASE4E1 -- PM Schedule Foundation.

Covers the backend-testable subset of Section J's 18 focused requirements:
server-side schedule-code generation and format (1-4), planned_activities
persistence and validation (5-6), the taxonomy shape (7-10), that existing
procedure values/columns are never silently rewritten (14), and that
schedule creation still issues exactly one INSERT, never touching
pm_occurrence (15). UI-facing requirements (11-13: no Schedule Code/
Checklist Template input, optional Notes) are covered by
CreatePMScheduleModal.test.jsx instead. Requirements 16-18 (pm_occurrence
workflow, Phase4B historical rendering, Phase4D manual PM behavior) are
proven by RE-RUNNING the pre-existing, untouched test suites for those
areas -- this phase does not modify any of that code, so no new test is
needed to prove it, only a rerun.

Same FakeRunner discipline as test_schedule_creation_never_creates_actual.py.
"""

import json
import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.operational_registry_repository import PMScheduleRepository  # noqa: E402
from API.pm_activity_catalog import (  # noqa: E402
    PM_ACTIVITY_FAMILIES,
    InvalidPlannedActivityError,
    validate_planned_activities,
)


class FakeRunner:
    """Returns `exists_response` to the first query_scalar call (the
    collision-check SELECT) and `insert_response` to every call after --
    matching the real call order inside PMScheduleRepository.create()."""

    def __init__(self, exists_response: str = "[]", insert_response: str = "[]"):
        self.scalar_calls: list[str] = []
        self.exists_response = exists_response
        self.insert_response = insert_response

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        return self.exists_response if len(self.scalar_calls) == 1 else self.insert_response


# --- 1/2/3: server-side generation, caller-optional, PMSCH-* format ---


def test_create_generates_a_schedule_code_when_caller_omits_it():
    runner = FakeRunner(exists_response="[]", insert_response=json.dumps([{"pm_schedule_code": "placeholder"}]))
    repo = PMScheduleRepository(runner)

    result = repo.create(
        values={
            "asset_code": "211-P-1A", "asset_type": "PUMP", "procedure": None, "frequency": "MONTHLY",
            "trigger_type": "CALENDAR",
        },
        actor="actor-1",
    )

    assert result is not None
    # Two scalar calls: one collision-check SELECT, one INSERT -- never a
    # second INSERT, never touching pm_occurrence.
    assert len(runner.scalar_calls) == 2
    exists_sql, insert_sql = runner.scalar_calls
    assert "SELECT" in exists_sql and "pm_schedule_code" in exists_sql
    assert "INSERT INTO public.pm_schedule" in insert_sql
    assert "INSERT INTO pm_occurrence" not in insert_sql
    # The generated code (embedded as a literal in the INSERT SQL) matches
    # the owner's mandated PMSCH-{12 uppercase hex} format.
    import re

    match = re.search(r"'(PMSCH-[0-9A-F]{12})'", insert_sql)
    assert match, f"no PMSCH-* literal found in INSERT SQL: {insert_sql}"


def test_create_honors_a_caller_supplied_code_without_generating_one():
    # Existing-caller compatibility: a caller that already supplies a code
    # (e.g. a future historical-import path) is never overridden, and no
    # collision-check SELECT is issued at all in that case.
    runner = FakeRunner(insert_response=json.dumps([{"pm_schedule_code": "PMS-LEGACY-1"}]))
    repo = PMScheduleRepository(runner)

    repo.create(
        values={
            "pm_schedule_code": "PMS-LEGACY-1", "asset_code": "211-P-1A", "procedure": "Inspect",
            "frequency": "MONTHLY", "trigger_type": "CALENDAR",
        },
        actor="actor-1",
    )

    assert len(runner.scalar_calls) == 1
    assert "'PMS-LEGACY-1'" in runner.scalar_calls[0]


def test_generated_code_retries_on_collision():
    # First candidate reports as already existing; the generator must
    # retry rather than reuse it (a schedule code is the table's PRIMARY
    # KEY -- silently colliding would corrupt an existing row).
    class CollidingRunner(FakeRunner):
        def query_scalar(self, sql: str) -> str:
            self.scalar_calls.append(sql)
            if len(self.scalar_calls) == 1:
                return json.dumps([{"present": 1}])  # first candidate: taken
            if len(self.scalar_calls) == 2:
                return "[]"  # second candidate: free
            return json.dumps([{"pm_schedule_code": "placeholder"}])

    runner = CollidingRunner()
    repo = PMScheduleRepository(runner)

    repo.create(
        values={"asset_code": "211-P-1A", "procedure": None, "frequency": "MONTHLY", "trigger_type": "CALENDAR"},
        actor="actor-1",
    )

    assert len(runner.scalar_calls) == 3  # 2 collision checks + 1 insert


# --- 4: existing read paths remain compatible (planned_activities added, nothing removed) ---


def test_list_and_get_select_planned_activities_alongside_every_pre_existing_column():
    runner = FakeRunner(insert_response="[]")
    repo = PMScheduleRepository(runner)

    repo.list_pm_schedules()
    list_sql = runner.scalar_calls[-1]
    repo.get_pm_schedule("PMS-1")
    get_sql = runner.scalar_calls[-1]

    for sql in (list_sql, get_sql):
        assert "p.planned_activities" in sql
        for pre_existing in ("p.pm_schedule_code", "p.procedure", "p.checklist", "p.last_performed", "p.status"):
            assert pre_existing in sql


# --- 5: planned_activities persists correctly, as JSONB, no done field ---


def test_planned_activities_persist_as_jsonb_with_no_done_field():
    runner = FakeRunner(insert_response=json.dumps([{"pm_schedule_code": "PMS-1"}]))
    repo = PMScheduleRepository(runner)

    repo.create(
        values={
            "pm_schedule_code": "PMS-1", "asset_code": "211-P-1A", "procedure": None, "frequency": "MONTHLY",
            "trigger_type": "CALENDAR",
            "planned_activities": [{"family": "Flushing Line", "variant": "DE", "code": "FLUSHING_LINE_DE"}],
        },
        actor="actor-1",
    )

    insert_sql = runner.scalar_calls[-1]
    assert "::jsonb" in insert_sql
    assert "FLUSHING_LINE_DE" in insert_sql
    assert "\\'done\\'" not in insert_sql
    assert '"done"' not in insert_sql


def test_create_with_no_planned_activities_stores_null():
    runner = FakeRunner(insert_response=json.dumps([{"pm_schedule_code": "PMS-1"}]))
    repo = PMScheduleRepository(runner)

    repo.create(
        values={
            "pm_schedule_code": "PMS-1", "asset_code": "211-P-1A", "procedure": None, "frequency": "MONTHLY",
            "trigger_type": "CALENDAR",
        },
        actor="actor-1",
    )

    insert_sql = runner.scalar_calls[-1]
    assert "NULL::jsonb" in insert_sql


# --- 6: server-side validator rejects a `done` field outright ---


def test_validate_planned_activities_rejects_a_done_field():
    with pytest.raises(InvalidPlannedActivityError):
        validate_planned_activities([{"family": "Flushing Line", "variant": "DE", "code": "FLUSHING_LINE_DE", "done": True}])


def test_validate_planned_activities_rejects_unknown_code():
    with pytest.raises(InvalidPlannedActivityError):
        validate_planned_activities([{"code": "NOT_A_REAL_CODE"}])


def test_validate_planned_activities_normalizes_family_and_variant_from_code():
    normalized = validate_planned_activities([{"code": "FLUSHING_LINE_DE"}])
    assert normalized == [{"family": "Flushing Line", "variant": "DE", "code": "FLUSHING_LINE_DE"}]


def test_validate_planned_activities_accepts_none_and_empty():
    assert validate_planned_activities(None) == []
    assert validate_planned_activities([]) == []


# --- 7/8/9/10: taxonomy shape ---


def test_seven_families_nineteen_variants():
    assert len(PM_ACTIVITY_FAMILIES) == 7
    assert sum(len(variants) for variants in PM_ACTIVITY_FAMILIES.values()) == 19


def test_general_de_nde_are_independent_per_family():
    for family in ("Flushing Line", "Quench Line", "Strainer", "Check Valve", "Cooler", "Cooling Water Cooler"):
        variants = PM_ACTIVITY_FAMILIES[family]
        assert set(variants.keys()) == {"GENERAL", "DE", "NDE"}
        assert len(set(variants.values())) == 3  # three distinct codes, none shared


def test_reservoir_is_general_only():
    assert set(PM_ACTIVITY_FAMILIES["Reservoir"].keys()) == {"GENERAL"}


def test_cooler_and_cooling_water_cooler_are_distinct_families():
    cooler_codes = set(PM_ACTIVITY_FAMILIES["Cooler"].values())
    cwc_codes = set(PM_ACTIVITY_FAMILIES["Cooling Water Cooler"].values())
    assert cooler_codes.isdisjoint(cwc_codes)


def test_no_wch_anywhere_in_the_catalog():
    for family, variants in PM_ACTIVITY_FAMILIES.items():
        assert "WCH" not in family.upper().replace(" ", "")
        for code in variants.values():
            assert "WCH" not in code


# --- 14: existing procedure values are never rewritten by an unrelated update ---


def test_update_never_touches_procedure_unless_explicitly_supplied():
    runner = FakeRunner(insert_response=json.dumps([{"pm_schedule_code": "PMS-1"}]))
    repo = PMScheduleRepository(runner)

    repo.update("PMS-1", values={"assigned_to": "Tech A"}, actor="actor-1")

    update_sql = runner.scalar_calls[-1]
    assert "procedure" not in update_sql


# --- 15: schedule creation issues exactly one INSERT, never pm_occurrence ---


def test_create_with_generated_code_never_inserts_into_pm_occurrence():
    runner = FakeRunner(exists_response="[]", insert_response=json.dumps([{"pm_schedule_code": "placeholder"}]))
    repo = PMScheduleRepository(runner)

    repo.create(
        values={"asset_code": "211-P-1A", "procedure": None, "frequency": "MONTHLY", "trigger_type": "CALENDAR"},
        actor="actor-1",
    )

    for sql in runner.scalar_calls:
        assert "INSERT INTO pm_occurrence" not in sql
    # exactly one call issues the pm_schedule INSERT (the other is the
    # collision-check SELECT)
    assert sum("INSERT INTO public.pm_schedule" in sql for sql in runner.scalar_calls) == 1
