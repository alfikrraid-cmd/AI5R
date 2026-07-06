from dataclasses import dataclass, field
from DIGITAL_EMPLOYEE.employee_identity import EmployeeIdentity
from DIGITAL_EMPLOYEE.employee_capability import EmployeeCapability


@dataclass
class DigitalEmployee:
    identity: EmployeeIdentity
    capability: EmployeeCapability
    status: str = field(default="CREATED")

    def initialize(self):
        self.status = "INITIALIZED"
        return self

    @property
    def name(self):
        return self.identity.name

    @property
    def organization(self):
        return self.identity.organization

    @property
    def department(self):
        return self.identity.department

    @property
    def position(self):
        return self.identity.position

    @property
    def role(self):
        return self.identity.position

    @property
    def identity_id(self):
        return getattr(self.identity, "identity_id", self.identity.name)
