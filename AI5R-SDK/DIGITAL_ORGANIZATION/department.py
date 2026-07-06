from dataclasses import dataclass, field
from DIGITAL_EMPLOYEE import DigitalEmployee


@dataclass
class Department:
    name: str
    manager: DigitalEmployee | None = None
    employees: list[DigitalEmployee] = field(default_factory=list)

    def add_employee(self, employee: DigitalEmployee):
        self.employees.append(employee)

    def employee_count(self) -> int:
        return len(self.employees)

    def assign_task(self, task: str):

        results = []

        for employee in self.employees:
            employee.assign(task)
            results.append(employee.execute())

        return results
