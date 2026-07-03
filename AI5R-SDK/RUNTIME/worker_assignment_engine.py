from typing import Dict, List, Optional

from RUNTIME.enterprise_task import EnterpriseTask


class WorkerAssignmentEngine:
    def __init__(self):
        self._workers: Dict[str, List[str]] = {}

    def register_worker(self, worker_id: str, capabilities: List[str]) -> None:
        self._workers[worker_id] = capabilities

    def assign(self, task: EnterpriseTask) -> Optional[str]:
        for worker_id, capabilities in self._workers.items():
            if task.task_type in capabilities:
                task.assign(worker_id)
                return worker_id
        return None

    def workers(self) -> Dict[str, List[str]]:
        return self._workers
