from __future__ import annotations

from typing import Any

from .collaboration_task import (
    CollaborationStatus,
    CollaborationTask,
)


class CollaborationManager:
    def __init__(self):
        self._tasks: dict[str, CollaborationTask] = {}

    def create_task(
        self,
        owner_employee_id: str,
        assigned_employee_id: str,
        title: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CollaborationTask:

        task = CollaborationTask(
            owner_employee_id=owner_employee_id,
            assigned_employee_id=assigned_employee_id,
            title=title,
            description=description,
            metadata=metadata or {},
        )

        self._tasks[task.task_id] = task
        return task

    def get_task(
        self,
        task_id: str,
    ) -> CollaborationTask | None:
        return self._tasks.get(task_id)

    def require_task(
        self,
        task_id: str,
    ) -> CollaborationTask:
        task = self.get_task(task_id)

        if task is None:
            raise KeyError(f"Task not found: {task_id}")

        return task

    def update_status(
        self,
        task_id: str,
        status: CollaborationStatus | str,
    ) -> CollaborationTask:

        task = self.require_task(task_id)
        return task.change_status(status)

    def list_tasks(
        self,
        employee_id: str | None = None,
    ) -> list[CollaborationTask]:

        if employee_id is None:
            return list(self._tasks.values())

        return [
            task
            for task in self._tasks.values()
            if task.owner_employee_id == employee_id
            or task.assigned_employee_id == employee_id
        ]

    def snapshot(self):
        return {
            task_id: task.snapshot()
            for task_id, task in self._tasks.items()
        }
