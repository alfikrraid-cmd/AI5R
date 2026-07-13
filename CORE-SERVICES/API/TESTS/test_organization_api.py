import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.organization_service import run_organization_goal


def test_run_organization_goal_returns_real_result(tmp_path):
    result = run_organization_goal(
        product_name="LTSA-BRAIN",
        goal_id="ORG-GOAL-001",
        root_path=tmp_path,
    )

    assert result["product"] == "LTSA-BRAIN"
    assert result["product_status"] == "RUNNING"
    assert result["organization_runtime_id"] == "ORG-RUN-ORG-GOAL-001"
    assert result["organization_status"] == "ACTIVE"
    assert result["work_unit_count"] == 2
    assert result["summary"]["employees"] == ["EMP-EXECUTOR", "EMP-PLANNER"]


def test_run_organization_goal_writes_runtime_state(tmp_path):
    run_organization_goal(
        product_name="LTSA-BRAIN",
        goal_id="ORG-GOAL-002",
        root_path=tmp_path,
    )

    runtime_state_path = tmp_path / "PRODUCTS" / "LTSA-BRAIN" / "runtime_state.json"

    assert runtime_state_path.exists()
