from dataclasses import dataclass
from typing import Any

from WORKFORCE.digital_employee import DigitalEmployee
from WORKFORCE.work_item import WorkItem
from WORKFORCE.employee_activity import EmployeeActivity
from WORKFORCE.employee_activity_registry import EmployeeActivityRegistry


@dataclass
class RuntimeResult:
    status: str
    employee_id: str
    work_item_id: str
    phase: str
    metadata: dict[str, Any]


class EmployeeRuntime:

    def __init__(self, activity_registry: EmployeeActivityRegistry | None = None) -> None:
        self.activity_registry = activity_registry or EmployeeActivityRegistry()

    def _record_activity(
        self,
        employee: DigitalEmployee,
        work_item: WorkItem,
        activity_type: str,
        status: str,
        message: str,
        progress: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.activity_registry.record(
            EmployeeActivity(
                employee_id=employee.employee_id,
                activity_type=activity_type,
                status=status,
                message=message,
                progress=progress,
                work_item_id=work_item.work_item_id,
                metadata=metadata or {},
            )
        )

    def __init__(self, activity_registry: EmployeeActivityRegistry | None = None) -> None:
        self.activity_registry = activity_registry or EmployeeActivityRegistry()

    def _record_activity(
        self,
        employee: DigitalEmployee,
        work_item: WorkItem,
        activity_type: str,
        status: str,
        message: str,
        progress: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.activity_registry.record(
            EmployeeActivity(
                employee_id=employee.employee_id,
                activity_type=activity_type,
                status=status,
                message=message,
                progress=progress,
                work_item_id=work_item.work_item_id,
                metadata=metadata or {},
            )
        )

    def receive_work(
        self,
        employee: DigitalEmployee,
        work_item: WorkItem,
    ) -> RuntimeResult:

        employee.metadata["runtime_state"] = "THINKING"
        self._record_activity(
            employee,
            work_item,
            activity_type="RECEIVED_WORK",
            status="THINKING",
            message="Employee received work item",
            progress=10,
        )

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

        objective_text = " ".join(
            [
                work_item.title,
                work_item.description,
                " ".join(work_item.metadata.values())
                if work_item.metadata
                else "",
            ]
        ).lower()

        selected_capabilities = [
            capability_id
            for capability_id in employee.capability_ids
            if capability_id.lower() in objective_text
        ]

        employee.metadata["runtime_state"] = "EXECUTING"
        employee.metadata["selected_capabilities"] = selected_capabilities
        self._record_activity(
            employee,
            work_item,
            activity_type="THINKING",
            status="CAPABILITY_SELECTED",
            message="Employee selected capabilities",
            progress=35,
            metadata={"selected_capabilities": selected_capabilities},
        )

        return RuntimeResult(
            status="OK",
            employee_id=employee.employee_id,
            work_item_id=work_item.work_item_id,
            phase="EXECUTING",
            metadata={
                "selected_capabilities": selected_capabilities,
            },
        )

    def execute(
        self,
        employee: DigitalEmployee,
        work_item: WorkItem,
    ) -> RuntimeResult:

        employee.metadata["runtime_state"] = "REVIEWING"
        self._record_activity(
            employee,
            work_item,
            activity_type="EXECUTING",
            status="REVIEWING",
            message="Employee completed execution step",
            progress=70,
        )

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
        self._record_activity(
            employee,
            work_item,
            activity_type="REVIEWING",
            status="LEARNING",
            message="Employee completed review step",
            progress=90,
        )

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
        self._record_activity(
            employee,
            work_item,
            activity_type="LEARNING",
            status="COMPLETED",
            message="Employee completed learning step",
            progress=100,
        )

        return RuntimeResult(
            status="COMPLETED",
            employee_id=employee.employee_id,
            work_item_id=work_item.work_item_id,
            phase="IDLE",
            metadata={},
        )

    def run(
        self,
        employee: DigitalEmployee,
        work_item: WorkItem,
    ) -> list[RuntimeResult]:
        results = []

        self.receive_work(employee, work_item)
        results.append(
            RuntimeResult("OK", employee.employee_id, work_item.work_item_id, "RECEIVED", {})
        )

        results.append(self.think(employee, work_item))
        results.append(self.execute(employee, work_item))
        results.append(self.review(employee, work_item))
        results.append(self.learn(employee, work_item))

        return results
