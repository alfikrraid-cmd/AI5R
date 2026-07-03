from RUNTIME.enterprise_task import EnterpriseTask


class DummyWorker:
    def execute(self, task: EnterpriseTask):
        return {
            "worker": "dummy",
            "status": "success",
            "task_type": task.task_type,
        }
