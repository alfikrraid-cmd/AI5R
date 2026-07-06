from dataclasses import dataclass, field
from typing import Any


@dataclass(init=False)
class DigitalEmployee:
    employee_id: str
    employee_name: str
    department: str
    role: str
    identity_id: str
    capabilities: list[str]
    status: str
    current_task: str | None

    def __init__(self, *args, **kwargs):
        self.capabilities = []
        self.status = "CREATED"
        self.current_task = None

        if len(args) == 2:
            identity, capability = args
            self.identity = identity
            self.capability = capability
            self.employee_id = getattr(identity, "employee_id", getattr(identity, "identity_id", identity.name))
            self.employee_name = identity.name
            self.department = identity.department
            self.role = identity.position
            self.identity_id = getattr(identity, "identity_id", self.employee_id)
            self.capabilities = list(getattr(capability, "capabilities", []))
            return

        self.employee_id = kwargs["employee_id"]
        self.employee_name = kwargs["employee_name"]
        self.department = kwargs["department"]
        self.role = kwargs["role"]
        self.identity_id = kwargs["identity_id"]

    @property
    def name(self):
        return self.employee_name

    def add_capability(self, capability: str):
        if capability not in self.capabilities:
            self.capabilities.append(capability)
        return self

    def remove_capability(self, capability: str):
        if capability in self.capabilities:
            self.capabilities.remove(capability)
        return self

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

    def execute(self):
        return {
            "employee": self.employee_name,
            "task": self.current_task,
            "status": "EXECUTED",
        }

    def complete(self):
        self.current_task = None
        self.status = "READY"
        return self

    def suspend(self):
        self.status = "SUSPENDED"
        return self

    def activate(self):
        self.status = "ACTIVE"
        return self
