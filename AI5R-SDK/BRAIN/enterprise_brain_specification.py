from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class EnterpriseBrainSpecification:
    """
    Canonical specification for Enterprise Brain Foundation v1.0.
    """

    specification_id: str = "EB-SPEC-001"

    name: str = "Enterprise Brain Specification"

    version: str = "1.0"

    status: str = "foundation_frozen"

    canonical_thread: List[str] = field(
        default_factory=lambda: [
            "reality",
            "observation",
            "understanding",
            "hypothesis",
            "decision",
            "planning",
            "execution",
            "outcome",
            "learning",
        ]
    )

    contracts: Dict[str, str] = field(
        default_factory=lambda: {
            "input_contract": "Reality Object",
            "output_contract": "Learning Object",
            "station_contract": "EnterpriseCognitiveStation",
            "runtime_contract": "EnterpriseBrainRuntime",
            "manufacturing_contract": "EnterpriseBrainManufacturingStation",
        }
    )

    principles: List[str] = field(
        default_factory=lambda: [
            "Everything is an Enterprise Object",
            "Every Process is a Station",
            "Enterprise Brain follows the Enterprise Cognitive Thread",
            "Enterprise Brain preserves the Digital Thread",
            "Enterprise Brain produces Enterprise Learning",
        ]
    )

    def to_dict(self):

        return {
            "specification_id": self.specification_id,
            "name": self.name,
            "version": self.version,
            "status": self.status,
            "canonical_thread": self.canonical_thread,
            "contracts": self.contracts,
            "principles": self.principles,
        }
