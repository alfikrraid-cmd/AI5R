from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_AI5R_SDK_PATH = Path(__file__).resolve().parents[2] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.MULTI_AGENT_COORDINATOR import MultiAgentCoordinator
from OSA.ORGANIZATION_RUNTIME import OrganizationRuntime
from PRODUCT_RUNTIME import ProductRuntime

DEFAULT_ROOT_PATH = Path(__file__).resolve().parents[2]


def run_organization_goal(
    product_name: str,
    goal_id: str,
    root_path: Path | str = DEFAULT_ROOT_PATH,
) -> dict[str, Any]:
    product_runtime = ProductRuntime(root_path)
    runtime_context = product_runtime.load(product_name, domains=["organization"])

    orchestrator = DigitalEmployeeOrchestrator()
    assignments = [
        orchestrator.assign(
            task={"task_id": f"{goal_id}-TASK-001"},
            capability_assignment={
                "employee_id": "EMP-PLANNER",
                "capability_id": "Planning",
            },
        ),
        orchestrator.assign(
            task={"task_id": f"{goal_id}-TASK-002"},
            capability_assignment={
                "employee_id": "EMP-EXECUTOR",
                "capability_id": "Execution",
            },
        ),
    ]

    coordination_result = MultiAgentCoordinator().coordinate(
        goal_id=goal_id,
        assignments=assignments,
    )

    organization_result = OrganizationRuntime().start(
        goal_id=goal_id,
        coordination_result=coordination_result,
    )

    return {
        "product": runtime_context["product"],
        "product_status": runtime_context["status"],
        "organization_runtime_id": organization_result.runtime_id,
        "organization_status": organization_result.status,
        "work_unit_count": organization_result.work_unit_count,
        "summary": organization_result.summary,
    }
