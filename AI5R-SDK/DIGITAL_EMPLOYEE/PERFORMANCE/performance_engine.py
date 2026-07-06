from __future__ import annotations

from .employee_performance import EmployeePerformance


class PerformanceEngine:
    def __init__(self):
        self._employees: dict[str, EmployeePerformance] = {}

    def register(
        self,
        employee_id: str,
    ) -> EmployeePerformance:

        if employee_id not in self._employees:
            self._employees[employee_id] = EmployeePerformance(
                employee_id=employee_id,
            )

        return self._employees[employee_id]

    def get(
        self,
        employee_id: str,
    ) -> EmployeePerformance | None:
        return self._employees.get(employee_id)

    def require(
        self,
        employee_id: str,
    ) -> EmployeePerformance:
        employee = self.get(employee_id)

        if employee is None:
            raise KeyError(
                f"Performance not found: {employee_id}"
            )

        return employee

    def record_success(
        self,
        employee_id: str,
    ) -> EmployeePerformance:
        employee = self.register(employee_id)
        employee.record_success()
        return employee

    def record_failure(
        self,
        employee_id: str,
    ) -> EmployeePerformance:
        employee = self.register(employee_id)
        employee.record_failure()
        return employee

    def ranking(self) -> list[EmployeePerformance]:
        return sorted(
            self._employees.values(),
            key=lambda x: (
                x.score,
                x.completed_tasks,
            ),
            reverse=True,
        )

    def snapshot(self):
        return {
            employee_id: employee.snapshot()
            for employee_id, employee
            in self._employees.items()
        }
