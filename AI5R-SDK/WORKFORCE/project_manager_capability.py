from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from WORKFORCE.digital_employee import DigitalEmployee
from WORKFORCE.sprint import Sprint
from WORKFORCE.work_item import WorkItem


SprintTask = WorkItem
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
            WorkItem(
                title="Design solution architecture",
                assigned_position_id="SOLUTION_ARCHITECT",
            ),
            WorkItem(
                title="Implement backend",
                assigned_position_id="BACKEND_ENGINEER",
            ),
            WorkItem(
                title="Implement frontend",
                assigned_position_id="FRONTEND_ENGINEER",
            ),
            WorkItem(
                title="Create quality tests",
                assigned_position_id="QA_ENGINEER",
            ),
            WorkItem(
                title="Prepare deployment",
                assigned_position_id="DEVOPS_ENGINEER",
            ),
            WorkItem(
                title="Document delivery",
                assigned_position_id="DOCUMENTATION_ENGINEER",
            ),
        ]

        for task in tasks:
            sprint.add_work_item(task)

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
