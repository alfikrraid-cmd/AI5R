"""
MWO-003.2
Organization -> Manufacturing Bridge

Deterministic, stateless orchestration wiring an injected
organization_runtime and manufacturing_runtime into a single work
order execution flow. Pure orchestration only: no business logic, no
LLM, no direct Worker import. Independent of the Manufacturing
Center's internals; reaches it only through the injected
manufacturing_runtime.
"""

from __future__ import annotations

from typing import Any

from ORGANIZATION.executive_work_order import ExecutiveWorkOrder


class DevelopmentManufacturingBridge:
    def __init__(
        self,
        organization_runtime: Any = None,
        manufacturing_runtime: Any = None,
    ) -> None:
        self.organization_runtime = organization_runtime
        self.manufacturing_runtime = manufacturing_runtime

    def execute(self, work_order: ExecutiveWorkOrder) -> Any:
        if not isinstance(work_order, ExecutiveWorkOrder):
            raise ValueError("work_order must be an ExecutiveWorkOrder")

        if self.organization_runtime is None:
            raise ValueError("organization_runtime is required")

        if self.manufacturing_runtime is None:
            raise ValueError("manufacturing_runtime is required")

        organization_result = self.organization_runtime.execute(work_order)
        return self.manufacturing_runtime.execute(organization_result)
