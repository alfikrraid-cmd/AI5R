from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from OSA.CAPABILITY_RESOLVER.capability_resolver import CapabilityResolver
from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.EXECUTION_DISPATCHER import ExecutionDispatcher
from OSA.MEMORY_LEARNING_ENGINE import MemoryLearningEngine
from OSA.REFLECTION_ENGINE import ReflectionEngine


@dataclass
class RuntimePipelineResult:
    pipeline_id: str
    goal_id: str
    task_count: int
    execution_count: int
    memory_count: int
    memories: list[Any] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class RuntimePlan:
    goal_id: str
    steps: list[str]


class RuntimePipeline:
    def __init__(self):
        self.capability_resolver = CapabilityResolver()
        self.orchestrator = DigitalEmployeeOrchestrator()
        self.dispatcher = ExecutionDispatcher()
        self.reflection_engine = ReflectionEngine()
        self.memory_engine = MemoryLearningEngine()

    def run(self, goal: dict[str, Any]) -> RuntimePipelineResult:
        goal_id = goal.get("goal_id")

        if not goal_id:
            raise ValueError("goal_id is required")

        plan = self._create_runtime_plan(goal)
        capability_assignments = self.capability_resolver.resolve(plan)

        memories = []

        for index, capability_assignment in enumerate(capability_assignments, start=1):
            task = {
                "task_id": f"TASK-{index:03d}",
                "goal_id": goal_id,
                "description": capability_assignment.step,
            }

            employee_assignment = self.orchestrator.assign(
                task=task,
                capability_assignment={
                    "employee_id": self._resolve_employee_id(capability_assignment.capability),
                    "capability_id": capability_assignment.capability,
                    "confidence": capability_assignment.confidence,
                },
            )

            execution_job = self.dispatcher.dispatch(employee_assignment)

            completed_job = self.dispatcher.complete(
                execution_job.execution_id,
                {
                    "output": f"Executed {task['task_id']}: {task['description']}",
                },
            )

            reflection = self.reflection_engine.reflect(completed_job)
            memory = self.memory_engine.learn(reflection)

            memories.append(memory)

        return RuntimePipelineResult(
            pipeline_id=f"PIPE-{goal_id}",
            goal_id=goal_id,
            task_count=len(plan.steps),
            execution_count=len(memories),
            memory_count=len(memories),
            memories=memories,
        )

    def _create_runtime_plan(self, goal: dict[str, Any]) -> RuntimePlan:
        goal_id = goal["goal_id"]
        desired_outcomes = goal.get("desired_outcomes") or []

        steps = [
            str(outcome)
            for outcome in desired_outcomes
            if str(outcome).strip()
        ]

        if not steps:
            description = str(goal.get("description", "")).strip()
            if description:
                steps = [description]

        if not steps:
            raise ValueError("goal description or desired_outcomes is required")

        return RuntimePlan(
            goal_id=goal_id,
            steps=steps,
        )

    def _resolve_employee_id(self, capability: str) -> str:
        capability_to_employee = {
            "MarketAnalysis": "EMP-MARKET",
            "ContentPlanning": "EMP-CONTENT",
            "FinancialPlanning": "EMP-FINANCE",
            "ExecutionManagement": "EMP-EXECUTION",
            "PerformanceEvaluation": "EMP-EVALUATION",
            "GeneralReasoning": "EMP-GENERAL",
        }

        return capability_to_employee.get(capability, "EMP-GENERAL")
