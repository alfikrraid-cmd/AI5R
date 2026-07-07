from __future__ import annotations

from OSA.RUNTIME_PIPELINE import RuntimePipeline


class OSACommandAPI:

    def __init__(self, runtime_pipeline=None):
        self.runtime_pipeline = runtime_pipeline or RuntimePipeline()

    def execute(
        self,
        prompt: str,
        employee_id: str = "EMP-001",
    ) -> dict:

        if not prompt or not prompt.strip():
            raise ValueError("prompt is required")

        result = self.runtime_pipeline.execute(
            command=prompt,
            employee_id=employee_id,
        )

        return {
            "status": "SUCCESS",
            "employee_id": employee_id,
            "prompt": prompt,
            "pipeline_id": result.pipeline_id,
            "goal_id": result.goal_id,
            "task_count": result.task_count,
            "execution_count": result.execution_count,
            "memory_count": result.memory_count,
            "memories": result.memories,
            "response": "Command accepted by Runtime Pipeline",
        }
