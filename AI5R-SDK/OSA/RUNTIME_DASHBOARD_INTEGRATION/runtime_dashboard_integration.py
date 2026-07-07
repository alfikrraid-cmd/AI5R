from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class RuntimeDashboardEvent:
    event_id: str
    event_type: str
    runtime_id: str
    goal_id: str
    status: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class RuntimeDashboardIntegration:
    def publish_runtime_started(self, runtime_result: Any) -> RuntimeDashboardEvent:
        return self._build_event("RUNTIME_STARTED", runtime_result)

    def publish_runtime_completed(self, runtime_result: Any) -> RuntimeDashboardEvent:
        return self._build_event("RUNTIME_COMPLETED", runtime_result)

    def publish_runtime_failed(self, runtime_result: Any) -> RuntimeDashboardEvent:
        return self._build_event("RUNTIME_FAILED", runtime_result)

    def _build_event(self, event_type: str, runtime_result: Any) -> RuntimeDashboardEvent:
        if runtime_result is None:
            raise ValueError("runtime_result is required")

        runtime_id = getattr(runtime_result, "runtime_id", "")
        goal_id = getattr(runtime_result, "goal_id", "")
        status = getattr(runtime_result, "status", "")

        if hasattr(status, "value"):
            status = status.value

        return RuntimeDashboardEvent(
            event_id=f"DASH-EVT-{uuid4().hex[:8].upper()}",
            event_type=event_type,
            runtime_id=runtime_id,
            goal_id=goal_id,
            status=str(status),
            payload={
                "runtime_id": runtime_id,
                "goal_id": goal_id,
                "status": str(status),
                "coordination_id": getattr(runtime_result, "coordination_id", None),
                "work_unit_count": getattr(runtime_result, "work_unit_count", None),
                "summary": getattr(runtime_result, "summary", {}),
            },
        )
