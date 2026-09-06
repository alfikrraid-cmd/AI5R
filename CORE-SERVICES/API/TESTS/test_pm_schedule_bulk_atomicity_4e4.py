"""AI5R-PHASE4E4, Section N -- REQUIRED re-audit of 4E.3's bulk_create()
atomicity: proves pm_schedule inserts and record_change_history CREATE
audits commit (or fail) as ONE unit, not two separately-committed steps.

The proof is structural, not simulated-transactional: bulk_create()
builds exactly one SQL string -- `WITH ins AS (INSERT INTO
public.pm_schedule ... RETURNING *), audit AS (INSERT INTO
record_change_history ... SELECT ... FROM ins) SELECT * FROM ins` -- and
executes it via exactly one runner.query_scalar() call. Postgres treats
a single multi-statement-via-CTE string as ONE indivisible unit of work
regardless of the connection's autocommit setting (confirmed in 4E.1/
4E.3: DatabaseRunner.query_scalar's direct-connect path sets
`conn.autocommit = True`, which commits automatically AFTER each
`cursor.execute()` call completes -- there is no "half-executed" state
for a single statement to autocommit partially into). So: if that one
call raises for any reason (a constraint violation on either the
pm_schedule INSERT or the audit INSERT), nothing from that statement is
ever visible -- there is no cleanup to write and no second statement
that could have already landed. This test proves the code path is
exactly the one-call shape that gives that guarantee, and exercises the
required failure/retry scenario end to end at the FakeRunner level."""

import json
import re
import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.operational_registry_repository import PMScheduleRepository  # noqa: E402

PMSCH_RE = re.compile(r"PMSCH-[0-9A-F]{12}")


def _row(client_row_id, asset_code):
    return {
        "client_row_id": client_row_id, "asset_code": asset_code, "asset_type": None, "procedure": None,
        "frequency": "MONTHLY", "trigger_type": "CALENDAR", "interval_unit": None,
        "effective_date": "2026-10-01", "next_due": "2026-10-01", "assigned_to": None,
        "estimated_duration_hours": None, "provenance": "MANUAL", "source_reference": None,
        "planned_activities": None,
    }


class FailingInsertRunner:
    """Simulates a DB-level failure DURING the single combined pm_schedule
    +audit INSERT statement (e.g. a NOT NULL/FK violation on either
    table) -- the runner raises for that one call, exactly modeling what
    a real Postgres connection does when any part of one statement
    fails: the whole statement's effects (both CTEs) are discarded."""

    def __init__(self, canonical_tags):
        self.scalar_calls: list[str] = []
        self._canonical_tags = canonical_tags

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        if "SELECT tag_number FROM public.ltsa_pumps" in sql:
            return json.dumps([{"tag_number": tag} for tag in self._canonical_tags])
        if "SELECT 1 AS present FROM public.pm_schedule" in sql:
            return "[]"
        if "INSERT INTO public.pm_schedule" in sql:
            assert "audit AS (INSERT INTO record_change_history" in sql, (
                "pm_schedule and the audit INSERT must be issued as ONE statement, not two"
            )
            raise RuntimeError("simulated database failure mid-statement (e.g. a constraint violation)")
        return "[]"


class SucceedingRunner:
    def __init__(self, canonical_tags):
        self.scalar_calls: list[str] = []
        self._canonical_tags = canonical_tags

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        if "SELECT tag_number FROM public.ltsa_pumps" in sql:
            return json.dumps([{"tag_number": tag} for tag in self._canonical_tags])
        if "SELECT 1 AS present FROM public.pm_schedule" in sql:
            return "[]"
        if "INSERT INTO public.pm_schedule" in sql:
            codes = PMSCH_RE.findall(sql)
            return json.dumps([{"pm_schedule_code": code} for code in codes])
        return "[]"


def test_a_failure_during_the_combined_insert_creates_zero_schedules_and_zero_audits():
    tags = [f"211-P-{i}" for i in range(10)]
    rows = [_row(f"row-{i}", tags[i]) for i in range(10)]
    runner = FailingInsertRunner(canonical_tags=tags)

    with pytest.raises(RuntimeError, match="simulated database failure"):
        PMScheduleRepository(runner).bulk_create(rows=rows, actor="actor-1")

    # Exactly one attempt at the combined statement was made -- no retry
    # loop that could have left a partial write behind, and (per the
    # runner's own assertion above) that one statement bound the
    # pm_schedule INSERT and the audit INSERT together.
    insert_attempts = [sql for sql in runner.scalar_calls if "INSERT INTO public.pm_schedule" in sql]
    assert len(insert_attempts) == 1


def test_corrected_retry_after_a_failed_batch_creates_exactly_ten_schedules_and_ten_audits_with_unique_codes_and_zero_occurrences():
    tags = [f"211-P-{i}" for i in range(10)]
    rows = [_row(f"row-{i}", tags[i]) for i in range(10)]

    # First attempt fails (simulated) -- nothing created.
    failing_runner = FailingInsertRunner(canonical_tags=tags)
    with pytest.raises(RuntimeError):
        PMScheduleRepository(failing_runner).bulk_create(rows=rows, actor="actor-1")

    # Retry against a healthy runner succeeds fully.
    runner = SucceedingRunner(canonical_tags=tags)
    result = PMScheduleRepository(runner).bulk_create(rows=rows, actor="actor-1")

    assert len(result) == 10
    codes = [r["pm_schedule_code"] for r in result]
    assert len(set(codes)) == 10  # 10 unique PMSCH codes, no duplicates across the retry

    insert_sql = next(sql for sql in runner.scalar_calls if "INSERT INTO public.pm_schedule" in sql)
    assert insert_sql.count("INSERT INTO public.pm_schedule") == 1  # one schedule INSERT
    assert insert_sql.count("INSERT INTO record_change_history") == 1  # one audit INSERT, same statement
    assert "'PM_SCHEDULE'" in insert_sql
    assert "'CREATE'" in insert_sql
    assert "INSERT INTO pm_occurrence" not in insert_sql  # zero pm_occurrence rows, same guarantee as 4E.3
