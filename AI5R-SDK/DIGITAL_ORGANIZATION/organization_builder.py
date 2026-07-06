from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .communication_runtime import CommunicationRuntime
from .delegation_runtime import DelegationRuntime
from .meeting_runtime import MeetingRuntime


@dataclass
class OrganizationRuntime:
    name: str
    departments: list[Any] = field(default_factory=list)
    employees: list[Any] = field(default_factory=list)
    workflows: list[Any] = field(default_factory=list)

    def __post_init__(self):
        self._communication = CommunicationRuntime()
        self._delegation = DelegationRuntime()
        self._meeting = MeetingRuntime()

    def add_department(self, department: Any):
        self.departments.append(department)
        return self

    def add_employee(self, employee: Any):
        self.employees.append(employee)
        return self

    def add_workflow(self, workflow: Any):
        self.workflows.append(workflow)
        return self

    def send_message(
        self,
        sender: str,
        receiver: str,
        content: str,
        message_type: str = "TASK",
    ):
        return self._communication.send(
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=message_type,
        )

    def delegate(
        self,
        delegator: str,
        delegatee: str,
        task: str,
    ):
        return self._delegation.delegate(
            delegator=delegator,
            delegatee=delegatee,
            task=task,
        )

    def schedule_meeting(
        self,
        title: str,
        participants: list[str],
        agenda: list[str],
    ):
        return self._meeting.schedule(
            title=title,
            participants=participants,
            agenda=agenda,
        )

    def status(self):
        return {
            "organization": self.name,
            "departments": len(self.departments),
            "employees": len(self.employees),
            "workflows": len(self.workflows),
            "messages": len(self._communication._messages),
            "delegations": len(self._delegation._delegations),
            "meetings": len(self._meeting._meetings),
        }


class OrganizationBuilder:
    """
    Builds an in-memory organization runtime without modifying
    existing DIGITAL_* public contracts.
    """

    def __init__(self, name: str):
        self._runtime = OrganizationRuntime(name=name)

    def add_department(self, department: Any):
        self._runtime.add_department(department)
        return self

    def add_employee(self, employee: Any):
        self._runtime.add_employee(employee)
        return self

    def add_workflow(self, workflow: Any):
        self._runtime.add_workflow(workflow)
        return self

    def build(self) -> OrganizationRuntime:
        return OrganizationRuntime(
            name=self._runtime.name,
            departments=list(self._runtime.departments),
            employees=list(self._runtime.employees),
            workflows=list(self._runtime.workflows),
        )
