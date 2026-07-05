import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PLANNING.planning_engine import PlanningEngine
from PLANNING.planning_validation_engine import PlanningValidationEngine


def test_planning_validation_engine():

    engine = PlanningEngine()
    validator = PlanningValidationEngine()

    plan = engine.create_plan(
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

    result = validator.validate(plan)

    assert result["valid"] is True
    assert result["errors"] == []

    print("PL-005 Planning Validation Engine OK")


if __name__ == "__main__":
    test_planning_validation_engine()
