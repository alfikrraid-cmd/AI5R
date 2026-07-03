from typing import List

from RUNTIME.enterprise_mission import EnterpriseMission
from RUNTIME.enterprise_task import EnterpriseTask
from RUNTIME.enterprise_worker import EnterpriseWorker
from RUNTIME.task_queue import TaskQueue
from RUNTIME.worker_assignment_engine import WorkerAssignmentEngine
from RUNTIME.task_execution_engine import TaskExecutionEngine


class MissionRuntime:
    def __init__(self):
        self.queue = TaskQueue()
        self.assignment_engine = WorkerAssignmentEngine()
        self.execution_engine = TaskExecutionEngine()

    def register_worker(self, worker: EnterpriseWorker):
        self.assignment_engine.register(worker)

    def load_tasks(self, tasks: List[EnterpriseTask]):
        for task in tasks:
            self.queue.enqueue(task)

    def run(self, mission: EnterpriseMission):
        mission.start()
        results = []

        while not self.queue.empty():
            task = self.queue.dequeue()
            worker = self.assignment_engine.assign(task)

            if worker is None:
                task.fail("No worker available")
                results.append(task.to_enterprise_object())
                continue

            result = self.execution_engine.execute(worker, task)
            results.append({
                "task": task.to_enterprise_object(),
                "result": result,
            })

        mission.complete()

        return {
            "mission": mission.to_enterprise_object(),
            "results": results,
        }
