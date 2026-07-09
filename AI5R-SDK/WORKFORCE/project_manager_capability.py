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
    assigned_employee_id: str | None = None
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
            raise ValueError(
                "Project manager requires TASK_BREAKDOWN capability"
            )

        tasks = [
            SprintTask(
                title="Design solution architecture",
                assigned_position_id="SOLUTION_ARCHITECT",
            ),
            SprintTask(
                title="Implement backend",
                assigned_position_id="BACKEND_ENGINEER",
            ),
            SprintTask(
                title="Implement frontend",
                assigned_position_id="FRONTEND_ENGINEER",
            ),
            SprintTask(
                title="Create quality tests",
                assigned_position_id="QA_ENGINEER",
            ),
            SprintTask(
                title="Prepare deployment",
                assigned_position_id="DEVOPS_ENGINEER",
            ),
            SprintTask(
                title="Document delivery",
                assigned_position_id="DOCUMENTATION_ENGINEER",
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

    def assign_tasks(
        self,
        project_manager: DigitalEmployee,
        tasks: list[SprintTask],
        employees: list[DigitalEmployee],
    ):

        if project_manager.position_id != "PROJECT_MANAGER":
            raise ValueError("Only PROJECT_MANAGER can assign tasks")

        assignments = []

        for task in tasks:

            candidates = [
                employee
                for employee in employees
                if employee.position_id == task.assigned_position_id
                and employee.status == "ACTIVE"
            ]

            if not candidates:
                assignments.append(
                    {
                        "task_id": task.task_id,
                        "status": "NO_EMPLOYEE_AVAILABLE",
                    }
                )
                continue

            employee = candidates[0]

            task.assigned_employee_id = employee.employee_id
            task.status = "ASSIGNED"

            assignments.append(
                {
                    "task_id": task.task_id,
                    "employee_id": employee.employee_id,
                    "position_id": employee.position_id,
                    "status": "ASSIGNED",
                }
            )

        return {
            "status": "ASSIGNMENT_COMPLETED",
            "assignments": assignments,
        }
