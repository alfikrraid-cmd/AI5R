from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol


class AgentRuntimeStatus(str, Enum):
    CREATED = "CREATED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


@dataclass
class AgentRuntimeRequest:
    request_id: str
    execution_id: str
    employee_id: str
    task_id: str
    instruction: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRuntimeResponse:
    response_id: str
    request_id: str
    status: AgentRuntimeStatus
    output: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AgentRuntimeProvider(Protocol):
    def execute(self, request: AgentRuntimeRequest) -> AgentRuntimeResponse:
        ...


class LocalEchoAgentRuntimeProvider:
    def execute(self, request: AgentRuntimeRequest) -> AgentRuntimeResponse:
        if not request.instruction:
            return AgentRuntimeResponse(
                response_id=f"RESP-{request.request_id}",
                request_id=request.request_id,
                status=AgentRuntimeStatus.FAILED,
                output="",
                metadata={"reason": "instruction is required"},
            )

        return AgentRuntimeResponse(
            response_id=f"RESP-{request.request_id}",
            request_id=request.request_id,
            status=AgentRuntimeStatus.EXECUTED,
            output=f"Executed instruction: {request.instruction}",
            metadata={
                "provider": "LocalEchoAgentRuntimeProvider",
                "execution_id": request.execution_id,
                "employee_id": request.employee_id,
                "task_id": request.task_id,
            },
        )


class AgentRuntimeAdapter:
    def __init__(self, provider: AgentRuntimeProvider | None = None):
        self.provider = provider or LocalEchoAgentRuntimeProvider()
        self.responses: dict[str, AgentRuntimeResponse] = {}

    def execute(self, request: AgentRuntimeRequest) -> AgentRuntimeResponse:
        response = self.provider.execute(request)
        self.responses[response.response_id] = response
        return response

    def execute_job(self, execution_job, instruction: str) -> AgentRuntimeResponse:
        request = AgentRuntimeRequest(
            request_id=f"REQ-{execution_job.execution_id}",
            execution_id=execution_job.execution_id,
            employee_id=execution_job.employee_id,
            task_id=execution_job.task_id,
            instruction=instruction,
            context={
                "execution_status": str(execution_job.status),
                "execution_result": execution_job.result,
            },
        )

        return self.execute(request)
