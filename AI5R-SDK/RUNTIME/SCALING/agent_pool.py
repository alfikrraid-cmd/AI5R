from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any
import threading


@dataclass
class AgentTask:
    agent_id: str
    task: Callable[[], Any]


class AgentPool:
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.queue: list[AgentTask] = []
        self.results: dict[str, Any] = {}
        self.lock = threading.Lock()

    def submit(self, agent_id: str, task: Callable[[], Any]):
        self.queue.append(AgentTask(agent_id, task))

    def _execute(self, task: AgentTask):
        result = task.task()
        with self.lock:
            self.results[task.agent_id] = result

    def run(self):
        threads = []

        for task in self.queue:
            t = threading.Thread(target=self._execute, args=(task,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return self.results

    def snapshot(self):
        return {
            "queue_size": len(self.queue),
            "results": dict(self.results),
        }
