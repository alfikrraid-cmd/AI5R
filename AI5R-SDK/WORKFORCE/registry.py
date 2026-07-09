from .worker import Worker


class WorkforceRegistry:
    def __init__(self) -> None:
        self._workers: dict[str, Worker] = {}

    def register(self, worker: Worker) -> Worker:
        if worker.worker_id in self._workers:
            raise ValueError(f"Worker already registered: {worker.worker_id}")
        self._workers[worker.worker_id] = worker
        return worker

    def get(self, worker_id: str) -> Worker:
        if worker_id not in self._workers:
            raise KeyError(f"Worker not found: {worker_id}")
        return self._workers[worker_id]

    def list_workers(self) -> list[Worker]:
        return list(self._workers.values())

    def find_available(
        self,
        required_role: str | None = None,
        required_skills: list[str] | None = None,
        department: str | None = None,
    ) -> list[Worker]:
        workers = self._workers.values()

        if department:
            workers = [worker for worker in workers if worker.department == department]

        return [
            worker
            for worker in workers
            if worker.can_handle(required_role=required_role, required_skills=required_skills)
        ]
