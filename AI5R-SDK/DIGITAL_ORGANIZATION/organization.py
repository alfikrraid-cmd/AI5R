from dataclasses import dataclass, field

from DIGITAL_ORGANIZATION.department import Department
from DIGITAL_ORGANIZATION.communication_runtime import CommunicationRuntime


@dataclass
class DigitalOrganization:
    name: str
    departments: list[Department] = field(default_factory=list)
    communication: CommunicationRuntime = field(default_factory=CommunicationRuntime)

    def add_department(self, department: Department):
        self.departments.append(department)

    def department_count(self):
        return len(self.departments)

    def get_department(self, name: str):
        for department in self.departments:
            if department.name == name:
                return department

        return None

    def send_message(
        self,
        sender: str,
        receiver: str,
        content: str,
        message_type: str = "TASK",
    ):
        return self.communication.send(
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=message_type,
        )

    def inbox(self, receiver: str):
        return self.communication.inbox(receiver)
