from typing import Dict, List, Optional
from .organization_worker import OrganizationWorker


class OrganizationWorkerRegistry:
    def __init__(self):
        self.workers: Dict[str, OrganizationWorker] = {}

    def register(self, worker: OrganizationWorker) -> OrganizationWorker:
        if worker.worker_id in self.workers:
            raise ValueError("Worker already registered")

        self.workers[worker.worker_id] = worker
        return worker

    def get(self, worker_id: str) -> Optional[OrganizationWorker]:
        return self.workers.get(worker_id)

    def list_by_organization(self, organization_id: str) -> List[OrganizationWorker]:
        return [
            worker for worker in self.workers.values()
            if worker.organization_id == organization_id
        ]

    def list_by_department(self, department_id: str) -> List[OrganizationWorker]:
        return [
            worker for worker in self.workers.values()
            if worker.department_id == department_id
        ]

    def find_by_capability(self, capability_key: str) -> List[OrganizationWorker]:
        return [
            worker for worker in self.workers.values()
            if capability_key in worker.capabilities
        ]
