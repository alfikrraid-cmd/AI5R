import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.DIGITAL_EMPLOYEE_ORCHESTRATOR import DigitalEmployeeOrchestrator
from OSA.EXECUTION_DISPATCHER import ExecutionDispatcher
from OSA.MEMORY_LEARNING_ENGINE import MemoryLearningEngine, MemoryLearningStatus
from OSA.REFLECTION_ENGINE import ReflectionEngine


def create_reflection_result():
    orchestrator = DigitalEmployeeOrchestrator()
    dispatcher = ExecutionDispatcher()

    assignment = orchestrator.assign(
        task={"task_id": "TASK-001"},
        capability_assignment={
            "employee_id": "EMP-001",
            "capability_id": "CAP-AI",
        },
    )

    job = dispatcher.dispatch(assignment)

    completed = dispatcher.complete(
        job.execution_id,
        {"output": "Campaign plan created"},
    )

    return ReflectionEngine().reflect(completed)


def test_memory_learning_engine_learns_from_reflection():
    reflection = create_reflection_result()

    memory = MemoryLearningEngine().learn(reflection)

    assert memory.memory_id == f"MEM-{reflection.reflection_id}"
    assert memory.reflection_id == reflection.reflection_id
    assert memory.execution_id == reflection.execution_id
    assert memory.employee_id == reflection.employee_id
    assert memory.task_id == reflection.task_id
    assert memory.status == MemoryLearningStatus.LEARNED
    assert memory.lesson == "Execution produced a usable output"


def test_memory_learning_engine_stores_memory():
    reflection = create_reflection_result()
    engine = MemoryLearningEngine()

    memory = engine.learn(reflection)

    assert engine.memories[memory.memory_id] == memory


def test_memory_learning_engine_can_ignore_reflection():
    reflection = create_reflection_result()

    memory = MemoryLearningEngine().ignore(reflection)

    assert memory.status == MemoryLearningStatus.IGNORED
    assert memory.lesson == "Reflection ignored and not used for learning"
