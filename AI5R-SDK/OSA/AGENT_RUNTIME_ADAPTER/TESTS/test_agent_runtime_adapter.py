import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.AGENT_RUNTIME_ADAPTER import (
    AgentRuntimeAdapter,
    AgentRuntimeRequest,
    AgentRuntimeStatus,
)
from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.EXECUTION_DISPATCHER import ExecutionDispatcher


def create_execution_job():
    orchestrator = DigitalEmployeeOrchestrator()
    dispatcher = ExecutionDispatcher()

    assignment = orchestrator.assign(
        task={
            "task_id": "TASK-001",
            "description": "Create campaign plan",
        },
        capability_assignment={
            "employee_id": "EMP-001",
            "capability_id": "ContentPlanning",
        },
    )

    return dispatcher.dispatch(assignment)


def test_agent_runtime_adapter_executes_request():
    adapter = AgentRuntimeAdapter()

    response = adapter.execute(
        AgentRuntimeRequest(
            request_id="REQ-001",
            execution_id="EXE-001",
            employee_id="EMP-001",
            task_id="TASK-001",
            instruction="Create campaign plan",
        )
    )

    assert response.response_id == "RESP-REQ-001"
    assert response.status == AgentRuntimeStatus.EXECUTED
    assert "Create campaign plan" in response.output


def test_agent_runtime_adapter_stores_response():
    adapter = AgentRuntimeAdapter()

    response = adapter.execute(
        AgentRuntimeRequest(
            request_id="REQ-002",
            execution_id="EXE-002",
            employee_id="EMP-002",
            task_id="TASK-002",
            instruction="Create content calendar",
        )
    )

    assert adapter.responses[response.response_id] == response


def test_agent_runtime_adapter_executes_execution_job():
    adapter = AgentRuntimeAdapter()
    job = create_execution_job()

    response = adapter.execute_job(
        execution_job=job,
        instruction="Create campaign plan",
    )

    assert response.status == AgentRuntimeStatus.EXECUTED
    assert response.metadata["execution_id"] == job.execution_id
    assert response.metadata["employee_id"] == "EMP-001"
    assert response.metadata["task_id"] == "TASK-001"


def test_agent_runtime_adapter_fails_empty_instruction():
    adapter = AgentRuntimeAdapter()

    response = adapter.execute(
        AgentRuntimeRequest(
            request_id="REQ-003",
            execution_id="EXE-003",
            employee_id="EMP-003",
            task_id="TASK-003",
            instruction="",
        )
    )

    assert response.status == AgentRuntimeStatus.FAILED
    assert response.metadata["reason"] == "instruction is required"
