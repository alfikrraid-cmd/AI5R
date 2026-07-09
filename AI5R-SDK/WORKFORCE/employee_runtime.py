from dataclasses import dataclass
from typing import Any

from WORKFORCE.digital_employee import DigitalEmployee
from WORKFORCE.work_item import WorkItem


@dataclass
class RuntimeResult:
    status: str
    employee_id: str
    work_item_id: str
    phase: str
    metadata: dict[str, Any]


class EmployeeRuntime:

    def receive_work(
        self,
        employee: DigitalEmployee,
        work_item: WorkItem,
    ) -> RuntimeResult:

        employee.metadata["runtime_state"] = "THINKING"

        return RuntimeResult(
            status="OK",
            employee_id=employee.employee_id,
            work_item_id=work_item.work_item_id,
            phase="THINKING",
            metadata={},
        )

    def think(
        self,
        employee: DigitalEmployee,
        work_item: WorkItem,
    ) -> RuntimeResult:

        employee.metadata["runtime_state"] = "EXECUTING"

        return RuntimeResult(
            status="OK",
            employee_id=employee.employee_id,
            work_item_id=work_item.work_item_id,
            phase="EXECUTING",
            metadata={},
        )

    def execute(
        self,
        employee: DigitalEmployee,
        work_item: WorkItem,
    ) -> RuntimeResult:

        employee.metadata["runtime_state"] = "REVIEWING"

        return RuntimeResult(
            status="OK",
            employee_id=employee.employee_id,
            work_item_id=work_item.work_item_id,
            phase="REVIEWING",
            metadata={},
        )

    def review(
        self,
        employee: DigitalEmployee,
        work_item: WorkItem,
    ) -> RuntimeResult:

        employee.metadata["runtime_state"] = "LEARNING"

        return RuntimeResult(
            status="OK",
            employee_id=employee.employee_id,
            work_item_id=work_item.work_item_id,
            phase="LEARNING",
            metadata={},
        )

    def learn(
        self,
        employee: DigitalEmployee,
        work_item: WorkItem,
    ) -> RuntimeResult:

        employee.metadata["runtime_state"] = "IDLE"

        return RuntimeResult(
            status="COMPLETED",
            employee_id=employee.employee_id,
            work_item_id=work_item.work_item_id,
            phase="IDLE",
            metadata={},
        )
