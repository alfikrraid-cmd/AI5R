from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class StudioLiveOpsSnapshot:
    status: str
    goals: list[dict[str, Any]]
    employees: list[dict[str, Any]]
    runtimes: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    memory: list[dict[str, Any]]
    events: list[dict[str, Any]]
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class StudioLiveOps:
    def build_snapshot(
        self,
        goals: list[dict[str, Any]] | None = None,
        employees: list[dict[str, Any]] | None = None,
        runtimes: list[dict[str, Any]] | None = None,
        tools: list[dict[str, Any]] | None = None,
        memory: list[dict[str, Any]] | None = None,
        events: list[dict[str, Any]] | None = None,
    ) -> StudioLiveOpsSnapshot:
        return StudioLiveOpsSnapshot(
            status="LIVE",
            goals=goals or [],
            employees=employees or [],
            runtimes=runtimes or [],
            tools=tools or [],
            memory=memory or [],
            events=events or [],
        )

    def build_from_runtime_result(self, runtime_result: Any) -> StudioLiveOpsSnapshot:
        if runtime_result is None:
            raise ValueError("runtime_result is required")

        goal_id = getattr(runtime_result, "goal_id", getattr(runtime_result, "goal", "UNKNOWN"))
        runtime_id = getattr(runtime_result, "runtime_id", "UNKNOWN")
        status = getattr(runtime_result, "status", "UNKNOWN")

        if hasattr(status, "value"):
            status = status.value

        return self.build_snapshot(
            goals=[
                {
                    "goal_id": goal_id,
                    "status": status,
                }
            ],
            runtimes=[
                {
                    "runtime_id": runtime_id,
                    "goal_id": goal_id,
                    "status": status,
                    "work_unit_count": getattr(runtime_result, "work_unit_count", None),
                    "summary": getattr(runtime_result, "summary", {}),
                }
            ],
            events=[
                {
                    "event_type": "STUDIO_RUNTIME_SNAPSHOT",
                    "runtime_id": runtime_id,
                    "goal_id": goal_id,
                    "status": status,
                }
            ],
        )
