from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable


class ToolStatus(str, Enum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


@dataclass
class ToolDefinition:
    tool_id: str
    name: str
    description: str = ""
    status: ToolStatus = ToolStatus.ENABLED
    metadata: dict[str, Any] = field(default_factory=dict)
    handler: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def execute(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.status == ToolStatus.DISABLED:
            raise RuntimeError(f"Tool is disabled: {self.tool_id}")

        if self.handler is None:
            return {
                "tool_id": self.tool_id,
                "status": "NO_HANDLER",
                "payload": payload or {},
            }

        return self.handler(payload or {})


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> ToolDefinition:
        if not tool.tool_id:
            raise ValueError("tool_id is required")

        if not tool.name:
            raise ValueError("name is required")

        self.tools[tool.tool_id] = tool
        return tool

    def get(self, tool_id: str) -> ToolDefinition:
        if tool_id not in self.tools:
            raise KeyError(f"Tool not found: {tool_id}")

        return self.tools[tool_id]

    def list_tools(self) -> list[ToolDefinition]:
        return list(self.tools.values())

    def enable(self, tool_id: str) -> ToolDefinition:
        tool = self.get(tool_id)
        tool.status = ToolStatus.ENABLED
        return tool

    def disable(self, tool_id: str) -> ToolDefinition:
        tool = self.get(tool_id)
        tool.status = ToolStatus.DISABLED
        return tool

    def execute(
        self,
        tool_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tool = self.get(tool_id)
        return tool.execute(payload)
