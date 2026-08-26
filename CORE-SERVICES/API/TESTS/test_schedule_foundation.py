import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from API.operational_registry_repository import PMScheduleRepository, ConditionMonitoringScheduleRepository


class Runner:
    def __init__(self):
        self.calls = []

    def query_scalar(self, sql):
        self.calls.append(sql)
        return json.dumps([{"schedule_code": "NEW", "asset_code": "P-1"}])


def test_pm_schedule_create_validates_canonical_pump_and_audits():
    runner = Runner()
    result = PMScheduleRepository(runner).create(
        values={"pm_schedule_code": "PMS-1", "asset_code": "P-1", "procedure": "Inspect", "frequency": "7", "trigger_type": "TIME"},
        actor="actor-1",
    )
    assert result["schedule_code"] == "NEW"
    assert "FROM public.ltsa_pumps" in runner.calls[0]
    assert "record_change_history" in runner.calls[0]


def test_pm_schedule_soft_delete_is_audited():
    runner = Runner()
    PMScheduleRepository(runner).soft_delete("PMS-1", actor="actor-1")
    assert "deleted_at = NOW()" in runner.calls[0]
    assert "'DELETE'" in runner.calls[0]


def test_cmon_schedule_create_validates_canonical_pump_and_audits():
    runner = Runner()
    result = ConditionMonitoringScheduleRepository(runner).create(
        values={"condition_monitoring_schedule_code": "CMS-1", "asset_code": "P-1", "monitoring_type": "VIBRATION"},
        actor="actor-1",
    )
    assert result["schedule_code"] == "NEW"
    assert "FROM public.ltsa_pumps" in runner.calls[0]
    assert "record_change_history" in runner.calls[0]


def test_cmon_schedule_soft_delete_is_audited():
    runner = Runner()
    ConditionMonitoringScheduleRepository(runner).soft_delete("CMS-1", actor="actor-1")
    assert "deleted_at = NOW()" in runner.calls[0]
    assert "'DELETE'" in runner.calls[0]
