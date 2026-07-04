from typing import Any, Dict

from .capability_engine import CapabilityEngine
from .capability_object import CapabilityObject
from .capability_registry import CapabilityRegistry
from .capability_validation_engine import CapabilityValidationEngine


class CapabilityRuntime:
    """
    Enterprise Capability Runtime

    Objective:
    Provide a single orchestration point for capability validation,
    registration, lookup, and execution.
    """

    def __init__(
        self,
        engine=None,
        registry=None,
        validation_engine=None,
    ):
        self.engine = engine or CapabilityEngine()
        self.registry = registry or CapabilityRegistry()
        self.validation_engine = validation_engine or CapabilityValidationEngine()

    def register(self, capability: CapabilityObject) -> Dict[str, Any]:
        validation = self.validation_engine.validate(capability)

        if not validation["valid"]:
            return {
                "status": "FAILED",
                "validation": validation,
                "capability": capability,
            }

        registered = self.registry.register(capability)

        return {
            "status": "REGISTERED",
            "validation": validation,
            "capability": registered,
        }

    def execute(
        self,
        capability_id: str,
        input_data: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        capability = self.registry.get(capability_id)

        if capability is None:
            return {
                "status": "FAILED",
                "reason": "Capability not found",
                "capability_id": capability_id,
            }

        return self.engine.execute(
            capability=capability,
            input_data=input_data,
        )

    def get(self, capability_id):
        return self.registry.get(capability_id)

    def list_all(self):
        return self.registry.list_all()

    def list_by_organization(self, organization_id):
        return self.registry.list_by_organization(organization_id)

    def list_by_domain(self, domain):
        return self.registry.list_by_domain(domain)
