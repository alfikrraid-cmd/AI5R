from typing import Any

from FACTORY.PIPELINE import PipelineOrchestrator, PipelineStep
from FACTORY.REGISTRY import StationRegistry


class BlueprintPipelineBuilder:
    def __init__(self, registry: StationRegistry):
        self.registry = registry

    def build(
        self,
        blueprint: dict[str, Any],
        runners: dict[str, Any],
    ) -> PipelineOrchestrator:
        if "pipeline" not in blueprint:
            raise ValueError("Blueprint requires pipeline section")

        pipeline = PipelineOrchestrator()

        for station_code in blueprint["pipeline"]:
            station = self.registry.get(station_code)

            if station_code not in runners:
                raise ValueError(f"Runner not found for station: {station_code}")

            pipeline.add_step(
                PipelineStep(
                    name=station.station_code,
                    runner=runners[station_code],
                )
            )

        return pipeline
