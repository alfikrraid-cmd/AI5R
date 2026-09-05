"""AI5R-PHASE4E1 -- PMScheduleCreateRequest model: pm_schedule_code and
procedure are optional (OWNER DECISIONS 1-2, 5), and planned_activities is
validated/normalized against the canonical Phase4D catalog, with a `done`
field rejected outright (OWNER DECISION 6/7, Section D)."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from models.requests import PMScheduleCreateRequest  # noqa: E402


def _base(**overrides):
    values = {"asset_code": "211-P-1A", "frequency": "MONTHLY", "trigger_type": "CALENDAR"}
    values.update(overrides)
    return values


def test_pm_schedule_code_is_optional():
    request = PMScheduleCreateRequest(**_base())
    assert request.pm_schedule_code is None


def test_procedure_is_optional():
    request = PMScheduleCreateRequest(**_base())
    assert request.procedure is None


def test_caller_supplied_code_and_procedure_are_still_honored():
    request = PMScheduleCreateRequest(**_base(pm_schedule_code="PMS-LEGACY-1", procedure="Inspect"))
    assert request.pm_schedule_code == "PMS-LEGACY-1"
    assert request.procedure == "Inspect"


def test_planned_activities_defaults_to_none():
    request = PMScheduleCreateRequest(**_base())
    assert request.planned_activities is None


def test_planned_activities_is_normalized_from_code_alone():
    request = PMScheduleCreateRequest(**_base(planned_activities=[{"code": "RESERVOIR"}]))
    assert request.planned_activities == [{"family": "Reservoir", "variant": "GENERAL", "code": "RESERVOIR"}]


def test_planned_activities_rejects_a_done_field():
    with pytest.raises(ValidationError):
        PMScheduleCreateRequest(**_base(planned_activities=[{"code": "RESERVOIR", "done": True}]))


def test_planned_activities_rejects_unknown_code():
    with pytest.raises(ValidationError):
        PMScheduleCreateRequest(**_base(planned_activities=[{"code": "NOT_REAL"}]))
