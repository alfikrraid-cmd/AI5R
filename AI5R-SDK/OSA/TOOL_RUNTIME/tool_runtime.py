from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from OSA.TOOL_REGISTRY import ToolRegistry


@dataclass(slots=True)
class ToolExecutionRequest:
    tool_name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class ToolExecutionResult:
    tool_name: str
    status: str
    output: Any


class ToolCallable(Protocol):
    def __call__(self, **kwargs) -> Any: ...


class ToolRuntime:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def execute(
        self,
        request: ToolExecutionRequest,
    ) -> ToolExecutionResult:

        if not request.tool_name:
            raise ValueError("tool_name is required")

        tool = self.registry.resolve(request.tool_name)

        result = tool(**request.arguments)

        return ToolExecutionResult(
            tool_name=request.tool_name,
            status="SUCCESS",
            output=result,
        )
