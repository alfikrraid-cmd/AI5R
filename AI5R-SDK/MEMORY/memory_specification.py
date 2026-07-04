from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class EnterpriseMemorySpecification:
    """
    Canonical specification for Enterprise Memory Foundation v1.0.
    """

    specification_id: str = "EM-SPEC-001"

    name: str = "Enterprise Memory Specification"

    version: str = "1.0"

    status: str = "foundation_frozen"

    canonical_pipeline: List[str] = field(
        default_factory=lambda: [
            "learning",
            "memory_engine",
            "validation",
            "registry",
            "query",
            "runtime",
        ]
    )

    contracts: Dict[str, str] = field(
        default_factory=lambda: {
            "input_contract": "Learning Object",
            "output_contract": "Memory Object",
            "runtime_contract": "MemoryRuntime",
            "pipeline_contract": "EnterpriseMemoryPipeline",
            "manufacturing_contract": "EnterpriseMemoryManufacturingStation",
        }
    )

    principles: List[str] = field(
        default_factory=lambda: [
            "Memory is produced from Learning",
            "Memory preserves the Digital Thread",
            "Memory must pass validation before registration",
            "Memory is queryable by learning_id, digital_thread_id, and confidence",
            "Enterprise Memory is an independent subsystem",
        ]
    )

    def to_dict(self):

        return {
            "specification_id": self.specification_id,
            "name": self.name,
            "version": self.version,
            "status": self.status,
            "canonical_pipeline": self.canonical_pipeline,
            "contracts": self.contracts,
            "principles": self.principles,
        }
