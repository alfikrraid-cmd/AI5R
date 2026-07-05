import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PLANNING.planning_runtime import PlanningRuntime


def test_planning_runtime():

    runtime = PlanningRuntime()

    result = runtime.create(
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

    plan = result["plan"]

    assert result["status"] == "CREATED"
    assert result["registration"]["status"] == "REGISTERED"
    assert plan.object_type == "PLAN"
    assert plan.status == "PLANNED"

    assert runtime.get(plan.plan_id) == plan
    assert runtime.list_all() == [plan]
    assert runtime.list_by_mission("MS-001") == [plan]

    print("PL-004 Planning Runtime OK")


if __name__ == "__main__":
    test_planning_runtime()
