from dataclasses import dataclass, field
from typing import List


@dataclass
class CompetencyManifest:
    """
    AI5R Competency Foundation Manifest

    Canonical description of the Competency subsystem.
    """

    subsystem: str = "COMPETENCY"
    foundation_version: str = "1.0"
    runtime: str = "CompetencyRuntime"
    registry: str = "CompetencyRegistry"

    engines: List[str] = field(default_factory=lambda: [
        "CompetencyMeasurementEngine",
        "CompetencyValidationEngine",
    ])

    objects: List[str] = field(default_factory=lambda: [
        "CompetencyObject",
    ])

    pipeline: List[str] = field(default_factory=lambda: [
        "CompetencyMeasurement",
        "CompetencyValidation",
        "CompetencyRegistry",
        "CompetencyQuery",
    ])

    depends_on: List[str] = field(default_factory=lambda: [
        "CAPABILITY",
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
            "depends_on": self.depends_on,
            "status": self.status,
        }
