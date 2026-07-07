from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from OSA.LLM_PROVIDER import LLMProviderRegistry, LLMRequest, MockLLMProvider
from OSA.RUNTIME_DASHBOARD_INTEGRATION import RuntimeDashboardIntegration


@dataclass
class AutonomousOrganizationRuntimeResult:
    goal_id: str
    runtime_result: Any
    llm_response: Any
    dashboard_events: list[Any]
    status: str


class AutonomousOrganizationRuntime:
    def __init__(
        self,
        organization_runtime: Any,
        llm_registry: LLMProviderRegistry | None = None,
        dashboard_integration: RuntimeDashboardIntegration | None = None,
    ):
        self.organization_runtime = organization_runtime
        self.llm_registry = llm_registry or LLMProviderRegistry()
        self.dashboard_integration = dashboard_integration or RuntimeDashboardIntegration()

        self.llm_registry.register(MockLLMProvider())

    def run(
        self,
        goal_id: str,
        coordination_result: Any,
        provider_name: str = "MOCK",
    ) -> AutonomousOrganizationRuntimeResult:
        if not goal_id:
            raise ValueError("goal_id is required")

        if coordination_result is None:
            raise ValueError("coordination_result is required")

        runtime_result = self.organization_runtime.start(
            goal_id=goal_id,
            coordination_result=coordination_result,
        )

        started_event = self.dashboard_integration.publish_runtime_started(runtime_result)

        llm_provider = self.llm_registry.resolve(provider_name)
        llm_response = llm_provider.generate(
            LLMRequest(
                prompt=f"Run autonomous organization for {goal_id}",
                metadata={
                    "goal_id": goal_id,
                    "runtime_id": runtime_result.runtime_id,
                },
            )
        )

        completed_result = self.organization_runtime.complete(runtime_result)
        completed_event = self.dashboard_integration.publish_runtime_completed(completed_result)

        return AutonomousOrganizationRuntimeResult(
            goal_id=goal_id,
            runtime_result=completed_result,
            llm_response=llm_response,
            dashboard_events=[
                started_event,
                completed_event,
            ],
            status="COMPLETED",
        )
