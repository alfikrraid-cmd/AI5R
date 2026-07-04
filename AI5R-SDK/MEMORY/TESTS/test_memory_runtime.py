import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.observation_engine import ObservationEngine
from BRAIN.understanding_engine import UnderstandingEngine
from BRAIN.hypothesis_engine import HypothesisEngine
from BRAIN.decision_engine import DecisionEngine
from BRAIN.planning_engine import PlanningEngine
from BRAIN.execution_engine import ExecutionEngine
from BRAIN.outcome_engine import OutcomeEngine
from BRAIN.learning_engine import LearningEngine

from MEMORY.memory_runtime import MemoryRuntime


def create_learning():

    reality = {
        "object_id": "reality-301",
        "object_type": "reality",
        "asset": "pump-301",
        "measurements": {
            "vibration": 15,
            "temperature": 95,
        },
        "findings": [
            "leak",
        ],
    }

    observation = ObservationEngine().observe(
        reality
    )

    understanding = UnderstandingEngine().understand(
        observation
    )

    hypothesis = HypothesisEngine().hypothesize(
        understanding
    )

    decision = DecisionEngine().decide(
        hypothesis
    )

    planning = PlanningEngine().process(
        decision
    )

    execution = ExecutionEngine().process(
        planning
    )

    outcome = OutcomeEngine().process(
        execution
    )

    return LearningEngine().process(
        outcome
    )


def test_memory_runtime():

    runtime = MemoryRuntime()

    learning = create_learning()

    memory = runtime.memorize(
        learning
    )

    assert runtime.count() == 1

    loaded = runtime.get(
        memory.memory_id
    )

    assert loaded.memory_id == memory.memory_id

    assert loaded.learning_id == learning.learning_id


def test_memory_runtime_query():

    runtime = MemoryRuntime()

    learning = create_learning()

    runtime.memorize(
        learning
    )

    results = runtime.query.by_learning_id(
        learning.learning_id
    )

    assert len(results) == 1
