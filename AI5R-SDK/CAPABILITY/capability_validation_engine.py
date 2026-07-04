from typing import Any, Dict, List

from .capability_object import CapabilityObject


class CapabilityValidationEngine:
    """
    Enterprise Capability Validation Engine

    Objective:
    Validate CapabilityObject before registration or execution.
    """

    REQUIRED_FIELDS = [
        "organization_id",
        "capability_code",
        "capability_name",
        "description",
    ]

    ALLOWED_STATUSES = [
        "ACTIVE",
        "INACTIVE",
        "DEPRECATED",
    ]

    def validate(self, capability: CapabilityObject) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        data = capability.to_dict()

        for field in self.REQUIRED_FIELDS:
            if not data.get(field):
                errors.append(f"Missing required field: {field}")

        if capability.status not in self.ALLOWED_STATUSES:
            errors.append("Invalid capability status")

        if not capability.supported_domains:
            warnings.append("Capability has no supported domains")

        if not capability.required_knowledge_ids:
            warnings.append("Capability has no required knowledge references")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "capability_id": capability.capability_id,
            "capability_code": capability.capability_code,
        }
