from dataclasses import dataclass, field
from typing import List


@dataclass
class CapabilityManifest:
    """
    AI5R Capability Foundation Manifest

    Canonical description of the Capability subsystem.
    """

    subsystem: str = "CAPABILITY"
    foundation_version: str = "1.0"
    runtime: str = "CapabilityRuntime"

    registry: str = "CapabilityRegistry"

    engines: List[str] = field(default_factory=lambda: [
        "CapabilityEngine",
        "CapabilityValidationEngine",
    ])

    objects: List[str] = field(default_factory=lambda: [
        "CapabilityObject",
    ])

    pipeline: List[str] = field(default_factory=lambda: [
        "CapabilityValidation",
        "CapabilityRegistry",
        "CapabilityExecution",
    ])

    status: str = "FROZEN_CANDIDATE"

    def to_dict(self):
        return {
            "subsystem": self.subsystem,
            "foundation_version": self.foundation_version,
            "runtime": self.runtime,
            "registry": self.registry,
            "engines": self.engines,
            "objects": self.objects,
            "pipeline": self.pipeline,
            "status": self.status,
        }
