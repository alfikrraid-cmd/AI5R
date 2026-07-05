from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.PIPELINE.blueprint_pipeline_builder import BlueprintPipelineBuilder
from FACTORY.REGISTRY import build_default_station_registry


def test_blueprint_pipeline_builder_builds_pipeline_from_blueprint():
    registry = build_default_station_registry()

    blueprint = {
        "product": {
            "name": "LTSA AI"
        },
        "pipeline": [
            "MS-001",
            "MS-002",
        ],
    }

    runners = {
        "MS-001": lambda payload: {"type": "REALITY_OBJECT", "payload": payload},
        "MS-002": lambda payload: {"type": "WAREHOUSE_OBJECT", "payload": payload},
    }

    pipeline = BlueprintPipelineBuilder(registry).build(
        blueprint=blueprint,
        runners=runners,
    )

    result = pipeline.run(
        {
            "source": "manual_input",
            "payload": {
                "observation": "test"
            },
        }
    )

    assert result.status == "COMPLETED"
    assert result.steps == ["MS-001", "MS-002"]
    assert result.outputs["MS-001"]["type"] == "REALITY_OBJECT"
    assert result.outputs["MS-002"]["type"] == "WAREHOUSE_OBJECT"


def test_blueprint_pipeline_builder_requires_pipeline_section():
    registry = build_default_station_registry()

    try:
        BlueprintPipelineBuilder(registry).build(
            blueprint={},
            runners={},
        )
    except ValueError as exc:
        assert str(exc) == "Blueprint requires pipeline section"
    else:
        raise AssertionError("Expected ValueError")


def test_blueprint_pipeline_builder_requires_runner():
    registry = build_default_station_registry()

    try:
        BlueprintPipelineBuilder(registry).build(
            blueprint={
                "pipeline": [
                    "MS-001"
                ]
            },
            runners={},
        )
    except ValueError as exc:
        assert str(exc) == "Runner not found for station: MS-001"
    else:
        raise AssertionError("Expected ValueError")
