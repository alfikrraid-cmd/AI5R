from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class EnterpriseBrainManifest:
    """
    Canonical manifest describing an Enterprise Brain.
    """

    brain_name: str = "Enterprise Brain"

    version: str = "1.0"

    enterprise_cognitive_thread: List[str] = field(
        default_factory=lambda: [
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

    supported_input: str = "reality"

    supported_output: str = "learning"

    metadata: Dict[str, str] = field(
        default_factory=lambda: {
            "manufacturer": "AI5R Factory",
            "architecture": "Enterprise Cognitive Thread",
            "type": "Enterprise Brain",
        }
    )

    def to_dict(self):

        return {
            "brain_name": self.brain_name,
            "version": self.version,
            "enterprise_cognitive_thread": self.enterprise_cognitive_thread,
            "supported_input": self.supported_input,
            "supported_output": self.supported_output,
            "metadata": self.metadata,
        }
