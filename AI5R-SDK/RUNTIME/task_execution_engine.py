from typing import Any, Dict, Protocol

from RUNTIME.enterprise_task import EnterpriseTask


class Worker(Protocol):
    def execute(self, task: EnterpriseTask) -> Dict[str, Any]:
        ...


class TaskExecutionEngine:
    def execute(self, worker: Worker, task: EnterpriseTask):
        task.start()

        try:
            result = worker.execute(task)
            task.complete(result)
            return result

        except Exception as exc:
            task.fail(str(exc))
            raise
