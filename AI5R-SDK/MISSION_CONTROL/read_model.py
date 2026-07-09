from dataclasses import dataclass, field


@dataclass
class MissionControlReadModel:

    mission: dict = field(default_factory=dict)

    organization: list = field(default_factory=list)

    timeline: list = field(default_factory=list)

    pipeline: list = field(default_factory=list)

    artifacts: list = field(default_factory=list)

    statistics: dict = field(default_factory=dict)

    def snapshot(self):

        return {
            "mission": self.mission,
            "organization": self.organization,
            "timeline": self.timeline,
            "pipeline": self.pipeline,
            "artifacts": self.artifacts,
            "statistics": self.statistics,
        }
