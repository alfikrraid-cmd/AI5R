"""
MWO-007
End-to-End Manufacturing Acceptance Demo

Deterministic, stateless orchestration wiring an injected CTO,
ProductManager, SolutionArchitect, ProductionLine, and
DigitalProductBundle builder into a single work order manufacturing
flow. Pure orchestration only: no business logic, no reasoning, no
LLM use, no global state, no filesystem writes.
"""

from __future__ import annotations

from typing import Any

from ORGANIZATION.executive_work_order import ExecutiveWorkOrder


class EndToEndManufacturingDemo:
    def __init__(
        self,
        cto: Any,
        product_manager: Any,
        solution_architect: Any,
        production_line: Any,
        bundle_builder: Any,
    ) -> None:
        self.cto = cto
        self.product_manager = product_manager
        self.solution_architect = solution_architect
        self.production_line = production_line
        self.bundle_builder = bundle_builder

    def manufacture(self, work_order: ExecutiveWorkOrder) -> Any:
        if not isinstance(work_order, ExecutiveWorkOrder):
            raise ValueError("work_order must be an ExecutiveWorkOrder")

        if self.cto is None:
            raise ValueError("cto is required")

        if self.product_manager is None:
            raise ValueError("product_manager is required")

        if self.solution_architect is None:
            raise ValueError("solution_architect is required")

        if self.production_line is None:
            raise ValueError("production_line is required")

        if self.bundle_builder is None:
            raise ValueError("bundle_builder is required")

        received_work_order = self.cto.receive_work(work_order)
        self.cto.plan(received_work_order)
        self.product_manager.plan(received_work_order)
        technical_architecture = self.solution_architect.plan(received_work_order)

        artifacts = self.production_line.produce(technical_architecture)

        product_name = technical_architecture.get("product_name")
        return self.bundle_builder.bundle(product_name, artifacts)
