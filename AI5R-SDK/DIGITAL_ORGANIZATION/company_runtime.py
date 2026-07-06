from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .organization_builder import OrganizationRuntime


@dataclass
class CompanyRuntime:
    """
    Top-level runtime for an AI5R digital company.
    """

    organization: OrganizationRuntime
    metadata: dict[str, Any] = field(default_factory=dict)
    state: str = "STOPPED"

    def boot(self):
        self.state = "RUNNING"
        return {
            "status": "RUNNING",
            "organization": self.organization.name,
        }

    def shutdown(self):
        self.state = "STOPPED"
        return {
            "status": "STOPPED",
            "organization": self.organization.name,
        }

    def health(self):
        return {
            "organization": self.organization.name,
            "state": self.state,
            "departments": len(self.organization.departments),
            "employees": len(self.organization.employees),
            "workflows": len(self.organization.workflows),
            "messages": self.organization.status()["messages"],
            "delegations": self.organization.status()["delegations"],
            "meetings": self.organization.status()["meetings"],
        }
