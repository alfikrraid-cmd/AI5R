from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .context_manager import ContextManager
from .identity_service import IdentityService
from .capability_service import CapabilityService
from .resource_manager import ResourceManager


@dataclass
class KernelRuntimeResult:
    runtime_id: str
    process_id: str
    identity_id: str
    capability_id: str
    resource_id: str
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    executed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class KernelRuntime:
    def __init__(
        self,
        context_manager: ContextManager | None = None,
        identity_service: IdentityService | None = None,
        capability_service: CapabilityService | None = None,
        resource_manager: ResourceManager | None = None,
    ):
        self.context_manager = context_manager or ContextManager()
        self.identity_service = identity_service or IdentityService()
        self.capability_service = capability_service or CapabilityService()
        self.resource_manager = resource_manager or ResourceManager()
        self._results: dict[str, KernelRuntimeResult] = {}

    def execute(
        self,
        runtime_id: str,
        process_id: str,
        identity_id: str,
        capability_id: str,
        resource_id: str,
        payload: dict[str, Any] | None = None,
    ) -> KernelRuntimeResult:
        if runtime_id in self._results:
            raise ValueError("runtime already exists")

        identity = self.identity_service.get(identity_id)
        if identity is None:
            raise ValueError("identity not found")

        capability = self.capability_service.get(capability_id)
        if capability is None:
            raise ValueError("capability not found")

        resource = self.resource_manager.get(resource_id)
        if resource is None:
            raise ValueError("resource not found")

        context = self.context_manager.get_process_context(process_id)
        if context is None:
            context = self.context_manager.create_context(
                process_id=process_id,
                data={},
                metadata={"created_by": "KernelRuntime"},
            )

        self.resource_manager.allocate(resource_id)

        result = KernelRuntimeResult(
            runtime_id=runtime_id,
            process_id=process_id,
            identity_id=identity_id,
            capability_id=capability_id,
            resource_id=resource_id,
            status="EXECUTED",
            output={
                "identity": identity.name,
                "capability": capability.capability_name,
                "resource": resource.resource_type,
                "payload": payload or {},
                "context_id": context.context_id,
            },
        )

        self.context_manager.update_context(
            context.context_id,
            data={
                "last_runtime_id": runtime_id,
                "last_status": result.status,
            },
        )

        self.resource_manager.release(resource_id)

        self._results[runtime_id] = result
        return result

    def get_result(self, runtime_id: str) -> KernelRuntimeResult | None:
        return self._results.get(runtime_id)

    def list_results(self) -> list[KernelRuntimeResult]:
        return list(self._results.values())
