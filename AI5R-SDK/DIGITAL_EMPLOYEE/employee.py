from DIGITAL_EMPLOYEE.employee_status import EmployeeStatus
from DIGITAL_EMPLOYEE.employee_identity import EmployeeIdentity
from DIGITAL_EMPLOYEE.employee_capability import EmployeeCapability
from DIGITAL_EMPLOYEE.employee_context import EmployeeContext


class DigitalEmployee:

    def __init__(
        self,
        identity: EmployeeIdentity,
        capability: EmployeeCapability,
        context: EmployeeContext | None = None,
    ):
        self.identity = identity
        self.capability = capability
        self.context = context or EmployeeContext()
        self.status = EmployeeStatus.CREATED

    def initialize(self):
        self.status = EmployeeStatus.INITIALIZED

    def ready(self):
        self.status = EmployeeStatus.READY

    def assign(self, task: str):
        self.task = task
        self.status = EmployeeStatus.WORKING

    def execute(self):
        return {
            "employee": self.identity.name,
            "position": self.identity.position,
            "task": self.task,
            "status": "EXECUTED",
        }

    def evaluate(self):
        self.status = EmployeeStatus.EVALUATED

    def learn(self):
        self.status = EmployeeStatus.LEARNING
