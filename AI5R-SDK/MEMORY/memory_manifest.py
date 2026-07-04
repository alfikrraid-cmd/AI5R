from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class EnterpriseMemoryManifest:
    """
    Canonical manifest describing the Enterprise Memory subsystem.
    """

    memory_name: str = "Enterprise Memory"

    version: str = "1.0"

    pipeline: List[str] = field(
        default_factory=lambda: [
            "learning",
            "memory_engine",
            "validation",
            "registry",
            "query",
            "runtime",
        ]
    )

    supported_input: str = "learning"

    supported_output: str = "memory"

    metadata: Dict[str, str] = field(
        default_factory=lambda: {
            "manufacturer": "AI5R Factory",
            "architecture": "Enterprise Memory",
            "type": "Enterprise Memory",
        }
    )

    def to_dict(self):

        return {

            "memory_name": self.memory_name,

            "version": self.version,

            "pipeline": self.pipeline,

            "supported_input": self.supported_input,

            "supported_output": self.supported_output,

            "metadata": self.metadata,
        }
