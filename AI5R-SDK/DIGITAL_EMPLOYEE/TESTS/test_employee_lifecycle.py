import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_EMPLOYEE import EmployeeLifecycle, EmployeeState


def test_employee_lifecycle_transitions():
    lifecycle = EmployeeLifecycle()

    assert lifecycle.state == EmployeeState.CREATED.value

    lifecycle.initialize()
    lifecycle.ready()
    lifecycle.plan()
    lifecycle.work()
    lifecycle.observe()
    lifecycle.learn()
    lifecycle.ready()

    assert lifecycle.state == EmployeeState.READY.value
    assert len(lifecycle.events) == 7
    assert lifecycle.events[0].from_state == "CREATED"
    assert lifecycle.events[-1].to_state == "READY"
