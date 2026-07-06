from dataclasses import dataclass, field

from .employee_identity import EmployeeIdentity
from .employee_capability import EmployeeCapability


@dataclass
class DigitalEmployee:
    identity: EmployeeIdentity
    capability: EmployeeCapability
    status: str = "CREATED"
    current_task: str | None = None

    def initialize(self):
        self.status = "INITIALIZED"
        return self

    def ready(self):
        self.status = "READY"
        return self

    def is_ready(self):
        return self.status == "READY"

    def assign(self, task: str):
        self.current_task = task
        self.status = "WORKING"
        return self

    def complete(self):
        self.status = "READY"
        self.current_task = None
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
