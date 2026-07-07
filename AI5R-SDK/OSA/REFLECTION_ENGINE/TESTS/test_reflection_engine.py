import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.EXECUTION_DISPATCHER import ExecutionDispatcher
from OSA.REFLECTION_ENGINE import ReflectionEngine, ReflectionStatus


def create_execution_job(result=None, failed=False):
    orchestrator = DigitalEmployeeOrchestrator()
    dispatcher = ExecutionDispatcher()

    assignment = orchestrator.assign(
        task={"task_id": "TASK-001"},
        capability_assignment={
            "employee_id": "EMP-001",
            "capability_id": "CAP-AI",
        },
    )

    job = dispatcher.dispatch(assignment)

    if failed:
        return dispatcher.fail(job.execution_id, "Tool timeout")

    if result is not None:
        return dispatcher.complete(job.execution_id, result)

    return job


def test_reflection_passes_successful_execution():
    job = create_execution_job({"output": "Campaign plan created"})

    reflection = ReflectionEngine().reflect(job)

    assert reflection.reflection_id == f"REF-{job.execution_id}"
    assert reflection.status == ReflectionStatus.PASSED
    assert reflection.score == 1.0
    assert reflection.execution_id == job.execution_id


def test_reflection_marks_empty_result_as_needs_improvement():
    job = create_execution_job()

    reflection = ReflectionEngine().reflect(job)

    assert reflection.status == ReflectionStatus.NEEDS_IMPROVEMENT
    assert reflection.score == 0.4


def test_reflection_fails_failed_execution():
    job = create_execution_job(failed=True)

    reflection = ReflectionEngine().reflect(job)

    assert reflection.status == ReflectionStatus.FAILED
    assert reflection.score == 0.0
