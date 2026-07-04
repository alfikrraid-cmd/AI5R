from typing import Any, Dict, List

from .competency_measurement_engine import CompetencyMeasurementEngine
from .competency_registry import CompetencyRegistry
from .competency_validation_engine import CompetencyValidationEngine


class CompetencyRuntime:
    """
    Enterprise Competency Runtime

    Objective:
    Provide a single orchestration point for measuring,
    validating, registering, and querying competency.
    """

    def __init__(
        self,
        measurement_engine=None,
        validation_engine=None,
        registry=None,
    ):
        self.measurement_engine = measurement_engine or CompetencyMeasurementEngine()
        self.validation_engine = validation_engine or CompetencyValidationEngine()
        self.registry = registry or CompetencyRegistry()

    def measure_and_register(
        self,
        organization_id: str,
        capability_id: str,
        competency_code: str,
        competency_name: str,
        executions: List[Dict[str, Any]],
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        competency = self.measurement_engine.measure(
            organization_id=organization_id,
            capability_id=capability_id,
            competency_code=competency_code,
            competency_name=competency_name,
            executions=executions,
            metadata=metadata,
        )

        validation = self.validation_engine.validate(competency)

        if not validation["valid"]:
            return {
                "status": "FAILED",
                "competency": competency,
                "validation": validation,
            }

        self.registry.register(competency)

        return {
            "status": "REGISTERED",
            "competency": competency,
            "validation": validation,
        }

    def register(self, competency):
        validation = self.validation_engine.validate(competency)

        if not validation["valid"]:
            return {
                "status": "FAILED",
                "competency": competency,
                "validation": validation,
            }

        self.registry.register(competency)

        return {
            "status": "REGISTERED",
            "competency": competency,
            "validation": validation,
        }

    def get(self, competency_id):
        return self.registry.get(competency_id)

    def list_all(self):
        return self.registry.list_all()

    def list_by_organization(self, organization_id):
        return self.registry.list_by_organization(organization_id)

    def list_by_capability(self, capability_id):
        return self.registry.list_by_capability(capability_id)

    def list_by_status(self, status):
        return self.registry.list_by_status(status)
