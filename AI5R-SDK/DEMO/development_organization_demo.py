"""
MWO-003.1
Development Organization Demo Runtime

Deterministic, stateless orchestration wiring an injected CTO and
ExecutiveRegistry into a single work order execution flow: receive,
plan, assign. Pure orchestration only, no reasoning and no LLM use.
Independent of the Manufacturing Center.
"""

from __future__ import annotations

from typing import Any

from ORGANIZATION.executive_work_order import ExecutiveWorkOrder
from ORGANIZATION.organization_execution_result import OrganizationExecutionResult


class DevelopmentOrganizationDemo:
    def __init__(self, cto: Any, executive_registry: Any) -> None:
        self.cto = cto
        self.executive_registry = executive_registry

    def run(self, work_order: ExecutiveWorkOrder) -> OrganizationExecutionResult:
        if not isinstance(work_order, ExecutiveWorkOrder):
            raise ValueError("work_order must be an ExecutiveWorkOrder")

        executive = self.executive_registry.get(self.cto.executive_id)
        if executive is None:
            raise ValueError("CTO not found in executive_registry")

        received = executive.receive_work(work_order)
        plan = executive.plan(received)
        assign_result = executive.assign(received)

        return OrganizationExecutionResult(
            status="COMPLETED",
            completed_roles=tuple(work_order.requested_roles),
            failed_roles=(),
            execution_order=tuple(work_order.requested_roles),
            results=(assign_result,),
            metadata={
                "executive_id": executive.executive_id,
                "work_order_id": work_order.work_order_id,
                "plan": plan,
            },
        )
