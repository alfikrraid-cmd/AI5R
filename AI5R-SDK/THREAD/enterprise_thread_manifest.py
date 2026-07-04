from dataclasses import dataclass, field
from typing import List


@dataclass
class EnterpriseThreadManifest:
    """
    AI5R Enterprise Thread Foundation Manifest

    Canonical description of the Thread subsystem.
    """

    subsystem: str = "THREAD"
    foundation_version: str = "1.0"
    runtime: str = "EnterpriseThreadRuntime"
    registry: str = "EnterpriseThreadRegistry"

    objects: List[str] = field(default_factory=lambda: [
        "EnterpriseThread",
    ])

    canonical_stations: List[str] = field(default_factory=lambda: [
        "MISSION",
        "INTENT",
        "ATTENTION",
        "FOCUS",
        "REALITY",
        "OBSERVATION",
        "UNDERSTANDING",
        "HYPOTHESIS",
        "DECISION",
        "PLANNING",
        "EXECUTION",
        "OUTCOME",
        "LEARNING",
        "WAREHOUSE",
        "EXPERIENCE",
        "MEMORY",
        "KNOWLEDGE",
        "CAPABILITY",
        "COMPETENCY",
        "INNOVATION",
    ])

    pipeline: List[str] = field(default_factory=lambda: [
        "ThreadCreation",
        "ThreadRegistration",
        "ThreadMovement",
        "ThreadClosure",
        "ThreadQuery",
    ])

    status: str = "FROZEN_CANDIDATE"

    def to_dict(self):
        return {
            "subsystem": self.subsystem,
            "foundation_version": self.foundation_version,
            "runtime": self.runtime,
            "registry": self.registry,
            "objects": self.objects,
            "canonical_stations": self.canonical_stations,
            "pipeline": self.pipeline,
            "status": self.status,
        }
