from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from OSA.CAPABILITY_RESOLVER import CapabilityResolver
from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.EXECUTION_DISPATCHER import ExecutionDispatcher
from OSA.GOAL_DECOMPOSITION_ENGINE import GoalDecompositionEngine
from OSA.GOAL_TASK_INTEGRATION import GoalTaskIntegration
from OSA.MEMORY_LEARNING_ENGINE import MemoryLearningEngine
from OSA.PLANNER_ENGINE import PlannerEngine
from OSA.REFLECTION_ENGINE import ReflectionEngine
from OSA.UNIVERSAL_TASK_ENGINE import UniversalTaskEngine


@dataclass
class RuntimePipelineResult:
    pipeline_id: str
    goal_id: str
    task_count: int
    execution_count: int
    memory_count: int
    memories: list[Any] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class RuntimePipeline:
    def __init__(self):
        self.goal_engine = GoalDecompositionEngine()
        self.task_engine = UniversalTaskEngine()
        self.goal_task_integration = GoalTaskIntegration(
            goal_engine=self.goal_engine,
            task_engine=self.task_engine,
        )
        self.planner = PlannerEngine()
        self.capability_resolver = CapabilityResolver()
        self.orchestrator = DigitalEmployeeOrchestrator()
        self.dispatcher = ExecutionDispatcher()
        self.reflection_engine = ReflectionEngine()
        self.memory_engine = MemoryLearningEngine()

    def run(self, goal: dict[str, Any]) -> RuntimePipelineResult:
        goal_id = goal.get("goal_id")

        if not goal_id:
            raise ValueError("goal_id is required")

        tasks = self.goal_task_integration.create_tasks_from_goal(goal)
        plan = self.planner.create_plan(goal_id=goal_id, tasks=tasks)

        memories = []

        for planned_task in plan.tasks:
            capability_assignment = self.capability_resolver.resolve(planned_task)

            employee_assignment = self.orchestrator.assign(
                task=planned_task,
                capability_assignment=capability_assignment,
            )

            execution_job = self.dispatcher.dispatch(employee_assignment)

            completed_job = self.dispatcher.complete(
                execution_job.execution_id,
                {
                    "output": f"Executed {planned_task['task_id']}",
                },
            )

            reflection = self.reflection_engine.reflect(completed_job)
            memory = self.memory_engine.learn(reflection)

            memories.append(memory)

        return RuntimePipelineResult(
            pipeline_id=f"PIPE-{goal_id}",
            goal_id=goal_id,
            task_count=len(tasks),
            execution_count=len(memories),
            memory_count=len(memories),
            memories=memories,
        )
