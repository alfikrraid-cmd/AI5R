from pathlib import Path
from typing import Any

from FACTORY.BLUEPRINT import ProductBlueprintLoader
from FACTORY.PIPELINE.blueprint_pipeline_builder import BlueprintPipelineBuilder
from FACTORY.PIPELINE.ltsa_ai_runners import build_ltsa_ai_runners
from FACTORY.REGISTRY import build_default_station_registry


class LTSAIBlueprintRuntime:
    def __init__(self, blueprint_path: str | Path):
        self.blueprint_path = blueprint_path

    def run(self, payload: dict[str, Any]):
        blueprint = ProductBlueprintLoader().load(self.blueprint_path)
        registry = build_default_station_registry()
        runners = build_ltsa_ai_runners()

        pipeline = BlueprintPipelineBuilder(registry).build(
            blueprint=blueprint,
            runners=runners,
        )

        return pipeline.run(payload)
