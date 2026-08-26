"""MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- "Schedule creation does NOT
create actual PM/CMON" (Phase 6 critical negative test). Proves it at the
SQL-shape level: creating a pm_schedule / condition_monitoring_schedule
row issues exactly one INSERT statement, into that schedule table only --
never into pm_occurrence / condition_monitoring_reading, and never a
second statement. Same FakeRunner discipline as
test_pm_occurrence_repository.py / test_condition_monitoring_reading_repository.py.
"""

import json
import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.operational_registry_repository import (  # noqa: E402
    ConditionMonitoringScheduleRepository,
    PMScheduleRepository,
)


class FakeRunner:
    def __init__(self, scalar_response: str = "[]"):
        self.scalar_calls: list[str] = []
        self.scalar_response = scalar_response

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        return self.scalar_response


def test_creating_a_pm_schedule_issues_exactly_one_statement_never_touching_pm_occurrence():
    runner = FakeRunner(scalar_response=json.dumps([{"pm_schedule_code": "PMS-1"}]))
    repo = PMScheduleRepository(runner)

    repo.create(
        values={
            "pm_schedule_code": "PMS-1", "asset_code": "211-P-1A", "asset_type": "PUMP",
            "procedure": "Seal Inspection", "frequency": "MONTHLY", "trigger_type": "CALENDAR",
            "interval_unit": None, "effective_date": "2026-09-01", "next_due": "2026-09-01",
            "assigned_to": None, "provenance": "MANUAL", "source_reference": None,
        },
        actor="actor-1",
    )

    assert len(runner.scalar_calls) == 1
    sql = runner.scalar_calls[0]
    assert "INSERT INTO public.pm_schedule" in sql
    assert "INSERT INTO pm_occurrence" not in sql
    assert "INSERT INTO condition_monitoring_reading" not in sql


def test_creating_a_condition_monitoring_schedule_issues_exactly_one_statement_never_touching_reading():
    runner = FakeRunner(scalar_response=json.dumps([{"condition_monitoring_schedule_code": "CMS-1"}]))
    repo = ConditionMonitoringScheduleRepository(runner)

    repo.create(
        values={
            "condition_monitoring_schedule_code": "CMS-1", "asset_code": "G-201-01A", "asset_type": "PUMP",
            "monitoring_type": "VIBRATION", "measurement_point": None, "frequency": "WEEKLY",
            "interval_unit": None, "effective_date": "2026-09-01", "next_due": "2026-09-01",
            "provenance": "MANUAL", "source_reference": None,
        },
        actor="actor-1",
    )

    assert len(runner.scalar_calls) == 1
    sql = runner.scalar_calls[0]
    assert "INSERT INTO public.condition_monitoring_schedule" in sql
    assert "INSERT INTO condition_monitoring_reading" not in sql
    assert "INSERT INTO pm_occurrence" not in sql


def test_creating_a_condition_monitoring_schedule_starts_at_the_default_status_never_client_supplied():
    # "status" is deliberately absent from ConditionMonitoringScheduleRepository
    # .create()'s own fields tuple -- a client can never dictate the
    # starting lifecycle state; it always begins at the column's own
    # DEFAULT 'PLANNED' (migration 029).
    runner = FakeRunner(scalar_response=json.dumps([{"condition_monitoring_schedule_code": "CMS-1"}]))
    repo = ConditionMonitoringScheduleRepository(runner)

    repo.create(
        values={
            "condition_monitoring_schedule_code": "CMS-1", "asset_code": "G-201-01A", "asset_type": "PUMP",
            "monitoring_type": "VIBRATION", "measurement_point": None, "frequency": "WEEKLY",
            "interval_unit": None, "effective_date": "2026-09-01", "next_due": "2026-09-01",
            "provenance": "MANUAL", "source_reference": None, "status": "COMPLETED",
        },
        actor="actor-1",
    )

    sql = runner.scalar_calls[0]
    assert "'COMPLETED'" not in sql
