from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from WORKFORCE.digital_employee import DigitalEmployee
from WORKFORCE.sprint import Sprint


@dataclass
class SprintTask:
    title: str
    assigned_position_id: str
    description: str = ""
    status: str = "CREATED"
    metadata: dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: f"TASK-{uuid4()}")


class ProjectManagerCapability:
    def breakdown_sprint(
        self,
        project_manager: DigitalEmployee,
        sprint: Sprint,
    ) -> dict[str, Any]:
        if project_manager.position_id != "PROJECT_MANAGER":
            raise ValueError("Only PROJECT_MANAGER can break down sprint")

        if "TASK_BREAKDOWN" not in project_manager.capability_ids:
            raise ValueError("Project manager requires TASK_BREAKDOWN capability")

        tasks = [
            SprintTask(
                title="Design solution architecture",
                assigned_position_id="SOLUTION_ARCHITECT",
                description=f"Create architecture plan for: {sprint.objective}",
            ),
            SprintTask(
                title="Implement backend",
                assigned_position_id="BACKEND_ENGINEER",
                description=f"Build backend capability for: {sprint.objective}",
            ),
            SprintTask(
                title="Implement frontend",
                assigned_position_id="FRONTEND_ENGINEER",
                description=f"Build user interface for: {sprint.objective}",
            ),
            SprintTask(
                title="Create quality tests",
                assigned_position_id="QA_ENGINEER",
                description=f"Validate quality for: {sprint.objective}",
            ),
            SprintTask(
                title="Prepare deployment",
                assigned_position_id="DEVOPS_ENGINEER",
                description=f"Prepare release workflow for: {sprint.objective}",
            ),
            SprintTask(
                title="Document delivery",
                assigned_position_id="DOCUMENTATION_ENGINEER",
                description=f"Document implementation for: {sprint.objective}",
            ),
        ]

        for task in tasks:
            sprint.add_task(task.task_id)

        return {
            "status": "TASKS_CREATED",
            "sprint_id": sprint.sprint_id,
            "project_manager_id": project_manager.employee_id,
            "tasks": tasks,
        }
