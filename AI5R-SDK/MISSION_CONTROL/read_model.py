from dataclasses import dataclass, field


@dataclass
class MissionControlReadModel:

    mission: dict = field(default_factory=dict)

    organization: dict = field(default_factory=dict)

    timeline: list = field(default_factory=list)

    pipeline: list = field(default_factory=list)

    artifacts: list = field(default_factory=list)

    statistics: dict = field(default_factory=dict)

    def snapshot(self):

        return {
            "mission": self.mission,
            "organization": list(self.organization.values()),
            "timeline": self.timeline,
            "pipeline": self.pipeline,
            "artifacts": self.artifacts,
            "statistics": self.statistics,
        }
