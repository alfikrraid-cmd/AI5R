from DIGITAL_ORGANIZATION.organization import DigitalOrganization
from DIGITAL_ORGANIZATION.department import Department
from DIGITAL_ORGANIZATION.communication_runtime import CommunicationRuntime
from DIGITAL_ORGANIZATION.delegation_runtime import DelegationRuntime
from DIGITAL_ORGANIZATION.meeting_runtime import MeetingRuntime


class OrganizationRuntime:

    def __init__(self, name: str):
        self.organization = DigitalOrganization(name=name)
        self.communication = CommunicationRuntime()
        self.delegation = DelegationRuntime()
        self.meeting = MeetingRuntime()

    def add_department(self, department: Department):
        self.organization.add_department(department)

        return {
            "status": "DEPARTMENT_ADDED",
            "department": department,
        }

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

    def delegate(
        self,
        delegator: str,
        delegatee: str,
        task: str,
    ):
        return self.delegation.delegate(
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
        return self.meeting.schedule(
            title=title,
            participants=participants,
            agenda=agenda,
        )

    def status(self):
        return {
            "organization": self.organization.name,
            "departments": self.organization.department_count(),
            "messages": len(self.communication._messages),
            "delegations": len(self.delegation._delegations),
            "meetings": len(self.meeting._meetings),
        }
