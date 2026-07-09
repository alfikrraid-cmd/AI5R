from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class DigitalEmployee:
    employee_name: str
    organization_id: str
    identity_id: str
    position_id: str
    kernel_id: str
    capability_ids: list[str] = field(default_factory=list)
    cognitive_function_ids: list[str] = field(default_factory=list)
    status: str = "ACTIVE"
    employment_type: str = "FULL_TIME"
    metadata: dict[str, Any] = field(default_factory=dict)
    object_type: str = "DIGITAL_EMPLOYEE"
    employee_id: str = field(default_factory=lambda: f"EMP-{uuid4()}")

    def execute_work_order(self, work_order: dict[str, Any]) -> dict[str, Any]:
        if self.status != "ACTIVE":
            raise ValueError("Digital employee must be ACTIVE to execute work order")

        objective = work_order.get("objective")
        if not objective:
            raise ValueError("Work order objective is required")

        execution_steps = [
            "UNDERSTAND_OBJECTIVE",
            "PLAN_WORK",
            "LOOKUP_CAPABILITIES",
            "CREATE_MANUFACTURING_REQUEST",
            "REVIEW_OUTPUT",
            "CAPTURE_EXPERIENCE",
        ]

        matched_capabilities = [
            capability_id
            for capability_id in self.capability_ids
            if capability_id.lower() in objective.lower()
        ]

        manufacturing_request = {
            "source": "DIGITAL_EMPLOYEE",
            "employee_id": self.employee_id,
            "organization_id": self.organization_id,
            "objective": objective,
            "payload": work_order.get("payload", {}),
        }

        experience_object = {
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "position_id": self.position_id,
            "objective": objective,
            "execution_steps": execution_steps,
            "matched_capabilities": matched_capabilities,
            "learned_capability_ids": work_order.get("learned_capability_ids", []),
            "metadata": work_order.get("metadata", {}),
        }

        for capability_id in experience_object["learned_capability_ids"]:
            if capability_id not in self.capability_ids:
                self.capability_ids.append(capability_id)

        return {
            "status": "EXECUTED",
            "employee_id": self.employee_id,
            "objective": objective,
            "execution_steps": execution_steps,
            "manufacturing_request": manufacturing_request,
            "experience_object": experience_object,
        }
