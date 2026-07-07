from __future__ import annotations

from dataclasses import asdict

from OSA.TASK_ENGINE import UniversalTaskEngine


class OSACommandAPI:
    def __init__(self, task_engine: UniversalTaskEngine | None = None):
        self.task_engine = task_engine or UniversalTaskEngine()

    def execute(self, prompt: str, employee_id: str = "EMP-001") -> dict:
        if not prompt or not prompt.strip():
            raise ValueError("prompt is required")

        clean_prompt = prompt.strip()
        task = self.task_engine.submit(
            goal=clean_prompt,
            employee_id=employee_id,
        )

        return {
            "status": "SUCCESS",
            "employee_id": employee_id,
            "prompt": clean_prompt,
            "task_id": task.task_id,
            "goal_id": task.goal_id,
            "stage": str(task.status.value if hasattr(task.status, "value") else task.status),
            "response": "Command accepted by OSA runtime pipeline",
            "task": asdict(task),
        }
