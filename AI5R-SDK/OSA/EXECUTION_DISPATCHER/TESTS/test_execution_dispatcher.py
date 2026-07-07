import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.EXECUTION_DISPATCHER import (
    ExecutionDispatcher,
    ExecutionStatus,
)


def create_assignment():
    orchestrator = DigitalEmployeeOrchestrator()

    return orchestrator.assign(
        task={
            "task_id": "TASK-001",
        },
        capability_assignment={
            "employee_id": "EMP-001",
            "capability_id": "CAP-AI",
        },
    )


def test_dispatch_execution():

    dispatcher = ExecutionDispatcher()

    assignment = create_assignment()

    job = dispatcher.dispatch(assignment)

    assert job.status == ExecutionStatus.RUNNING
    assert job.employee_id == "EMP-001"


def test_complete_execution():

    dispatcher = ExecutionDispatcher()

    assignment = create_assignment()

    job = dispatcher.dispatch(assignment)

    finished = dispatcher.complete(
        job.execution_id,
        {
            "output": "hello world"
        }
    )

    assert finished.status == ExecutionStatus.SUCCESS
    assert finished.result["output"] == "hello world"


def test_failed_execution():

    dispatcher = ExecutionDispatcher()

    assignment = create_assignment()

    job = dispatcher.dispatch(assignment)

    failed = dispatcher.fail(
        job.execution_id,
        "Tool timeout"
    )

    assert failed.status == ExecutionStatus.FAILED
    assert failed.result["reason"] == "Tool timeout"
