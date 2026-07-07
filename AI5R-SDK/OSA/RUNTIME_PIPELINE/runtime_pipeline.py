from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from OSA.API.CONVERSATION.conversation_api import OSAConversationAPI
from OSA.CAPABILITY_RESOLVER.capability_resolver import CapabilityResolver
from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.EXECUTION_DISPATCHER import ExecutionDispatcher
from OSA.EVENT_BUS_INTEGRATION import OSAEventBusIntegration, OSAEventType
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
    summary: dict[str, Any] = field(default_factory=dict)
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
        self.conversation_api = OSAConversationAPI()
        self.event_bus = OSAEventBusIntegration()

    def execute(self, command: str, employee_id: str = "EMP-001") -> RuntimePipelineResult:
        clean_command = str(command).strip()

        if not clean_command:
            raise ValueError("command is required")

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")

        conversation = self.conversation_api.process(clean_command)

        result = self.run(
            {
                "goal_id": f"CMD-{timestamp}",
                "description": clean_command,
                "desired_outcomes": [conversation.recommendation],
                "employee_id": employee_id,
            }
        )

        result.summary["command"] = clean_command
        result.summary["employee_id"] = employee_id
        result.summary["conversation_message"] = conversation.message
        result.summary["conversation_recommendation"] = conversation.recommendation

        return result

    def run(self, goal: dict[str, Any]) -> RuntimePipelineResult:
        goal_id = goal.get("goal_id")

        if not goal_id:
            raise ValueError("goal_id is required")

        self.event_bus.publish(
            OSAEventType.PIPELINE_STARTED,
            source="RuntimePipeline",
            payload={"goal_id": goal_id},
        )

        plan = self._create_runtime_plan(goal)
        capability_assignments = self.capability_resolver.resolve(plan)

        self.event_bus.publish(
            OSAEventType.CAPABILITY_RESOLVED,
            source="RuntimePipeline",
            payload={
                "goal_id": goal_id,
                "assignment_count": len(capability_assignments),
            },
        )

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

            self.event_bus.publish(
                OSAEventType.EMPLOYEE_ASSIGNED,
                source="RuntimePipeline",
                payload={
                    "goal_id": goal_id,
                    "task_id": task["task_id"],
                    "employee_id": employee_assignment.employee_id,
                },
            )

            execution_job = self.dispatcher.dispatch(employee_assignment)

            completed_job = self.dispatcher.complete(
                execution_job.execution_id,
                {
                    "output": f"Executed {task['task_id']}: {task['description']}",
                },
            )

            self.event_bus.publish(
                OSAEventType.EXECUTION_COMPLETED,
                source="RuntimePipeline",
                payload={
                    "goal_id": goal_id,
                    "task_id": task["task_id"],
                    "execution_id": completed_job.execution_id,
                },
            )

            reflection = self.reflection_engine.reflect(completed_job)

            self.event_bus.publish(
                OSAEventType.REFLECTION_CREATED,
                source="RuntimePipeline",
                payload={
                    "goal_id": goal_id,
                    "task_id": task["task_id"],
                    "execution_id": completed_job.execution_id,
                },
            )
            memory = self.memory_engine.learn(reflection)

            self.event_bus.publish(
                OSAEventType.MEMORY_LEARNED,
                source="RuntimePipeline",
                payload={
                    "goal_id": goal_id,
                    "task_id": task["task_id"],
                },
            )

            memories.append(memory)

        self.event_bus.publish(
            OSAEventType.PIPELINE_COMPLETED,
            source="RuntimePipeline",
            payload={
                "goal_id": goal_id,
                "task_count": len(plan.steps),
                "memory_count": len(memories),
            },
        )

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
