from __future__ import annotations

from OSA.CAPABILITY_RESOLVER.capability_assignment import CapabilityAssignment

from .employee_assignment import EmployeeAssignment


class EmployeeOrchestrator:
    def assign(
        self,
        assignments: list[CapabilityAssignment],
    ) -> list[EmployeeAssignment]:
        if not assignments:
            raise ValueError("Capability assignments are required")

        employee_assignments = []

        for assignment in assignments:
            employee_id, employee_role = self._select_employee(
                assignment.capability
            )

            employee_assignments.append(
                EmployeeAssignment(
                    step=assignment.step,
                    capability=assignment.capability,
                    employee_id=employee_id,
                    employee_role=employee_role,
                    confidence=0.85,
                )
            )

        return employee_assignments

    def _select_employee(self, capability: str) -> tuple[str, str]:
        if capability == "MarketAnalysis":
            return "EMP-003", "Research Analyst"

        if capability == "ContentPlanning":
            return "EMP-001", "Marketing Strategist"

        if capability == "FinancialPlanning":
            return "EMP-002", "Finance Analyst"

        if capability == "ExecutionManagement":
            return "EMP-004", "Execution Manager"

        if capability == "PerformanceEvaluation":
            return "EMP-005", "Performance Analyst"

        return "EMP-000", "General AI Worker"
