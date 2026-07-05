import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PLANNING.planning_object import PlanningObject


def test_planning_object():

    plan = PlanningObject(
        mission_id="MS-001",
        goal="Reduce pump downtime",
        required_capabilities=[
            "CAP-001",
            "CAP-005",
        ],
        execution_steps=[
            {
                "step": 1,
                "action": "Inspect Pump",
            },
            {
                "step": 2,
                "action": "Generate Report",
            },
        ],
    )

    assert plan.object_type == "PLAN"
    assert plan.status == "PLANNED"
    assert len(plan.execution_steps) == 2

    print("PL-001 Planning Object OK")


if __name__ == "__main__":
    test_planning_object()
