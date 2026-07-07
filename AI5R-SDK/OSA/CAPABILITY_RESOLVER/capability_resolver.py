from __future__ import annotations

from OSA.PLANNER.plan_object import PlanObject

from .capability_assignment import CapabilityAssignment


class CapabilityResolver:
    def resolve(self, plan: PlanObject) -> list[CapabilityAssignment]:
        if not plan.steps:
            raise ValueError("Plan steps are required")

        assignments = []

        for step in plan.steps:
            capability = self._infer_capability(step)

            assignments.append(
                CapabilityAssignment(
                    step=step,
                    capability=capability,
                    confidence=0.80,
                )
            )

        return assignments

    def _infer_capability(self, step: str) -> str:
        text = step.lower()

        if "market" in text or "customer" in text:
            return "MarketAnalysis"

        if "content" in text or "campaign" in text:
            return "ContentPlanning"

        if "budget" in text or "financial" in text or "cost" in text:
            return "FinancialPlanning"

        if "execute" in text or "implementation" in text:
            return "ExecutionManagement"

        if "evaluate" in text or "result" in text:
            return "PerformanceEvaluation"

        return "GeneralReasoning"
