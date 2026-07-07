from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class MemoryLearningStatus(str, Enum):
    CREATED = "CREATED"
    LEARNED = "LEARNED"
    IGNORED = "IGNORED"


@dataclass
class LearnedMemory:
    memory_id: str
    reflection_id: str
    execution_id: str
    employee_id: str
    task_id: str
    status: MemoryLearningStatus
    lesson: str
    source: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class MemoryLearningEngine:
    def __init__(self):
        self.memories: dict[str, LearnedMemory] = {}

    def learn(self, reflection_result) -> LearnedMemory:
        if not reflection_result.reflection_id:
            raise ValueError("reflection_id is required")

        memory_id = f"MEM-{reflection_result.reflection_id}"

        memory = LearnedMemory(
            memory_id=memory_id,
            reflection_id=reflection_result.reflection_id,
            execution_id=reflection_result.execution_id,
            employee_id=reflection_result.employee_id,
            task_id=reflection_result.task_id,
            status=MemoryLearningStatus.LEARNED,
            lesson=self._extract_lesson(reflection_result),
            source={
                "score": reflection_result.score,
                "status": str(reflection_result.status),
                "insights": reflection_result.insights,
                "metadata": reflection_result.metadata,
            },
        )

        self.memories[memory_id] = memory
        return memory

    def ignore(self, reflection_result) -> LearnedMemory:
        if not reflection_result.reflection_id:
            raise ValueError("reflection_id is required")

        memory_id = f"MEM-{reflection_result.reflection_id}"

        memory = LearnedMemory(
            memory_id=memory_id,
            reflection_id=reflection_result.reflection_id,
            execution_id=reflection_result.execution_id,
            employee_id=reflection_result.employee_id,
            task_id=reflection_result.task_id,
            status=MemoryLearningStatus.IGNORED,
            lesson="Reflection ignored and not used for learning",
            source={
                "score": reflection_result.score,
                "status": str(reflection_result.status),
                "insights": reflection_result.insights,
            },
        )

        self.memories[memory_id] = memory
        return memory

    def _extract_lesson(self, reflection_result) -> str:
        if reflection_result.insights:
            return reflection_result.insights[0]

        return "No explicit insight was available"
