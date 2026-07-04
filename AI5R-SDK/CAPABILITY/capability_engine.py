from typing import Any, Dict

from .capability_object import CapabilityObject


class CapabilityEngine:
    """
    Enterprise Capability Engine

    Objective:
    Execute a CapabilityObject as an enterprise callable capability.
    """

    def execute(
        self,
        capability: CapabilityObject,
        input_data: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if capability.status != "ACTIVE":
            return {
                "status": "FAILED",
                "reason": "Capability is not active",
                "capability_id": capability.capability_id,
                "capability_code": capability.capability_code,
            }

        return {
            "status": "EXECUTED",
            "capability_id": capability.capability_id,
            "capability_code": capability.capability_code,
            "capability_name": capability.capability_name,
            "input_data": input_data or {},
            "metadata": capability.metadata,
        }
