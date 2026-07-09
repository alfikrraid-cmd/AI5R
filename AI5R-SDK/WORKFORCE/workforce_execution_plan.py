from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class WorkforceExecutionPlan:
    mission_id: str
    work_queue: list[str] = field(default_factory=list)
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    running: list[str] = field(default_factory=list)
    waiting: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    plan_id: str = field(default_factory=lambda: f"WEP-{uuid4()}")
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def add_work_item(self, work_item_id: str, dependencies: list[str] | None = None) -> None:
        if work_item_id not in self.work_queue:
            self.work_queue.append(work_item_id)

        self.dependency_graph[work_item_id] = dependencies or []

        if dependencies:
            if work_item_id not in self.blocked:
                self.blocked.append(work_item_id)
        else:
            if work_item_id not in self.waiting:
                self.waiting.append(work_item_id)

        self.updated_at = _now()

    def mark_running(self, work_item_id: str) -> None:
        self._move(work_item_id, source_lists=[self.waiting, self.blocked], target_list=self.running)
        self.updated_at = _now()

    def mark_completed(self, work_item_id: str) -> None:
        self._move(work_item_id, source_lists=[self.running, self.waiting, self.blocked], target_list=self.completed)
        self._unblock_ready_items()
        self.updated_at = _now()

    def ready_items(self) -> list[str]:
        return [
            work_item_id
            for work_item_id in self.waiting
            if work_item_id not in self.running
            and work_item_id not in self.completed
        ]

    def _unblock_ready_items(self) -> None:
        for work_item_id in list(self.blocked):
            dependencies = self.dependency_graph.get(work_item_id, [])
            if all(dependency in self.completed for dependency in dependencies):
                self.blocked.remove(work_item_id)
                if work_item_id not in self.waiting:
                    self.waiting.append(work_item_id)

    def _move(self, work_item_id: str, source_lists: list[list[str]], target_list: list[str]) -> None:
        for source in source_lists:
            if work_item_id in source:
                source.remove(work_item_id)

        if work_item_id not in target_list:
            target_list.append(work_item_id)

    def snapshot(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "mission_id": self.mission_id,
            "work_queue": self.work_queue,
            "dependency_graph": self.dependency_graph,
            "running": self.running,
            "waiting": self.waiting,
            "blocked": self.blocked,
            "completed": self.completed,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
