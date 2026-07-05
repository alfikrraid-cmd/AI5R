import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PLANNING.planning_engine import PlanningEngine


def test_planning_engine():

    engine = PlanningEngine()

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
        metadata={"owner": "AI5R"},
    )

    assert plan.object_type == "PLAN"
    assert plan.status == "PLANNED"
    assert plan.mission_id == "MS-001"
    assert plan.goal == "Reduce pump downtime"
    assert plan.required_capabilities == ["CAP-005"]
    assert plan.execution_steps[0]["capability_code"] == "CAP-005"
    assert plan.metadata["owner"] == "AI5R"

    print("PL-002 Planning Engine OK")


if __name__ == "__main__":
    test_planning_engine()
