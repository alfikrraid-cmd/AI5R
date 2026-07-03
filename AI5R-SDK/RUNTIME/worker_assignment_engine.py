from typing import List, Optional

from RUNTIME.enterprise_task import EnterpriseTask
from RUNTIME.enterprise_worker import EnterpriseWorker


class WorkerAssignmentEngine:

    def __init__(self):
        self._workers: List[EnterpriseWorker] = []

    def register(self, worker: EnterpriseWorker):
        self._workers.append(worker)

    def assign(self, task: EnterpriseTask) -> Optional[EnterpriseWorker]:
        for worker in self._workers:
            if worker.supports(task.task_type):
                task.assign(worker.worker_id)
                return worker

        return None

    def workers(self):
        return self._workers
