import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PLANNING.planning_runtime import PlanningRuntime
from INTEGRATION.pipeline_validation_engine import PipelineValidationEngine


def test_pipeline_validation_engine():

    planning_runtime = PlanningRuntime()
    validator = PipelineValidationEngine()

    result = planning_runtime.create(
        mission_id="MS-001",
        goal="Reduce pump downtime",
        required_capabilities=["CAP-005"],
        execution_steps=[
            {
                "step": 1,
                "action": "Inspect Pump",
                "capability_code": "CAP-005",
            }
        ],
    )

    validation = validator.validate_plan(result["plan"])

    assert validation["valid"] is True
    assert validation["errors"] == []

    print("EI-002 Pipeline Validation Engine OK")


if __name__ == "__main__":
    test_pipeline_validation_engine()
