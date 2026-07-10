"""
AO-010
Product Manager

Concrete AIExecutive responsible for product domain oversight.

Stateless and deterministic: holds only an injected OrganizationRuntime
reference and delegates all orchestration to it. No AI reasoning, no
LLM use, no prompt generation, no Manufacturing Center dependency.
"""

from __future__ import annotations

from typing import Any

from ORGANIZATION.ai_executive import AIExecutive
from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

EXECUTIVE_ID = "EXEC-PM-001"
EXECUTIVE_NAME = "Product Manager"
DEPARTMENT = "PRODUCT"
AUTHORITY_LEVEL = "C-LEVEL"


class ProductManager(AIExecutive):
    def __init__(self, organization_runtime: Any = None) -> None:
        super().__init__(
            executive_id=EXECUTIVE_ID,
            executive_name=EXECUTIVE_NAME,
            department=DEPARTMENT,
            authority_level=AUTHORITY_LEVEL,
        )
        object.__setattr__(self, "organization_runtime", organization_runtime)

    def receive_work(
        self, work_order: ExecutiveWorkOrder
    ) -> ExecutiveWorkOrder:
        if not isinstance(work_order, ExecutiveWorkOrder):
            raise ValueError("work_order must be an ExecutiveWorkOrder")

        return work_order

    def plan(self, work_order: ExecutiveWorkOrder) -> dict[str, Any]:
        if not isinstance(work_order, ExecutiveWorkOrder):
            raise ValueError("work_order must be an ExecutiveWorkOrder")

        return {
            "product_name": work_order.metadata.get(
                "product_name", work_order.work_order_id
            ),
            "objective": work_order.objective,
            "features": list(work_order.requested_roles),
            "constraints": list(work_order.constraints),
            "priority": work_order.priority,
        }

    def assign(self, work_order: ExecutiveWorkOrder) -> Any:
        if not isinstance(work_order, ExecutiveWorkOrder):
            raise ValueError("work_order must be an ExecutiveWorkOrder")

        if self.organization_runtime is None:
            raise ValueError(
                "organization_runtime is required to assign work"
            )

        return self.organization_runtime.assign(work_order)

    def monitor(self) -> dict[str, Any]:
        return {
            "executive_id": self.executive_id,
            "department": self.department,
            "authority_level": self.authority_level,
            "status": "MONITORING",
        }

    def report(self, result: Any) -> dict[str, Any]:
        return {
            "executive_id": self.executive_id,
            "department": self.department,
            "result": result,
        }
