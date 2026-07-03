from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4


@dataclass
class OrganizationRuntimeContext:
    organization_id: str
    runtime_name: str
    department_id: Optional[str] = None
    worker_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    object_type: str = "ORGANIZATION_RUNTIME_CONTEXT"
    runtime_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "ACTIVE"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return self.__dict__


class MultiOrganizationRuntime:
    def __init__(self):
        self.contexts: Dict[str, OrganizationRuntimeContext] = {}
        self.active_organization_id: Optional[str] = None

    def register_context(
        self,
        context: OrganizationRuntimeContext
    ) -> OrganizationRuntimeContext:
        if context.runtime_id in self.contexts:
            raise ValueError("Runtime context already registered")

        self.contexts[context.runtime_id] = context
        return context

    def get_context(self, runtime_id: str) -> Optional[OrganizationRuntimeContext]:
        return self.contexts.get(runtime_id)

    def activate_organization(self, organization_id: str):
        self.active_organization_id = organization_id
        return {
            "active_organization_id": self.active_organization_id,
            "status": "ACTIVE",
        }

    def list_contexts_by_organization(self, organization_id: str):
        return [
            context for context in self.contexts.values()
            if context.organization_id == organization_id
        ]

    def isolate(self, organization_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "organization_id": organization_id,
            "isolated": True,
            "payload": payload,
        }
