import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PLANNING.planning_engine import PlanningEngine
from PLANNING.planning_registry import PlanningRegistry


def test_planning_registry():

    engine = PlanningEngine()
    registry = PlanningRegistry()

    plan = engine.create_plan(
        mission_id="MS-001",
        goal="Reduce pump downtime",
        required_capabilities=["CAP-005"],
    )

    registration = registry.register(plan)

    assert registration["status"] == "REGISTERED"
    assert registration["plan_id"] == plan.plan_id
    assert registry.get(plan.plan_id) == plan
    assert registry.list_all() == [plan]
    assert registry.list_by_mission("MS-001") == [plan]

    print("PL-003 Planning Registry OK")


if __name__ == "__main__":
    test_planning_registry()
