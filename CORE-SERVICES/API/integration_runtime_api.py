from __future__ import annotations

from dataclasses import asdict
from typing import Any

from OSA.AUTONOMOUS_ORGANIZATION_RUNTIME import AutonomousOrganizationRuntime
from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.MULTI_AGENT_COORDINATOR import MultiAgentCoordinator
from OSA.ORGANIZATION_RUNTIME import OrganizationRuntime
from OSA.STUDIO_API_ADAPTER import StudioAPIAdapter
from OSA.STUDIO_EVENT_STREAM import StudioEventStream
from OSA.STUDIO_LIVE_OPS import StudioLiveOps


class IntegrationRuntimeAPI:
    def __init__(self):
        self.event_stream = StudioEventStream()
        self.studio_live_ops = StudioLiveOps()
        self.studio_api_adapter = StudioAPIAdapter()
        self.organization_runtime = OrganizationRuntime()
        self.autonomous_runtime = AutonomousOrganizationRuntime(
            organization_runtime=self.organization_runtime,
        )

    def run_goal(self, goal_id: str) -> dict[str, Any]:
        if not goal_id:
            raise ValueError("goal_id is required")

        self.event_stream.publish(
            "GOAL_RECEIVED",
            {
                "goal_id": goal_id,
            },
        )

        coordination_result = self._create_coordination_result(goal_id)

        result = self.autonomous_runtime.run(
            goal_id=goal_id,
            coordination_result=coordination_result,
        )

        self.event_stream.publish(
            "AUTONOMOUS_RUNTIME_COMPLETED",
            {
                "goal_id": goal_id,
                "runtime_id": result.runtime_result.runtime_id,
                "status": result.status,
            },
        )

        snapshot = self.studio_live_ops.build_from_runtime_result(
            result.runtime_result,
        )

        payload = self.studio_api_adapter.serialize_snapshot(snapshot)
        payload["events"] = [
            asdict(event)
            for event in self.event_stream.latest()
        ]

        return payload

    def health(self) -> dict[str, str]:
        return {
            "status": "OK",
            "service": "AI5R Integration Runtime API",
        }

    def _create_coordination_result(self, goal_id: str):
        orchestrator = DigitalEmployeeOrchestrator()

        assignments = [
            orchestrator.assign(
                task={
                    "task_id": f"{goal_id}-TASK-001",
                },
                capability_assignment={
                    "employee_id": "EMP-PLANNER",
                    "capability_id": "Planning",
                },
            ),
            orchestrator.assign(
                task={
                    "task_id": f"{goal_id}-TASK-002",
                },
                capability_assignment={
                    "employee_id": "EMP-EXECUTOR",
                    "capability_id": "Execution",
                },
            ),
        ]

        return MultiAgentCoordinator().coordinate(
            goal_id=goal_id,
            assignments=assignments,
        )
