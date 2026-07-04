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

from MEMORY.memory_engine import MemoryEngine
from MEMORY.memory_registry import MemoryRegistry


def create_memory():

    reality = {
        "object_id": "reality-201",
        "object_type": "reality",
        "asset": "pump-201",
        "measurements": {
            "vibration": 15,
            "temperature": 95,
        },
        "findings": [
            "leak",
        ],
    }

    observation = ObservationEngine().observe(reality)

    understanding = UnderstandingEngine().understand(observation)

    hypothesis = HypothesisEngine().hypothesize(understanding)

    decision = DecisionEngine().decide(hypothesis)

    planning = PlanningEngine().process(decision)

    execution = ExecutionEngine().process(planning)

    outcome = OutcomeEngine().process(execution)

    learning = LearningEngine().process(outcome)

    return MemoryEngine().memorize(learning)


def test_memory_registry():

    registry = MemoryRegistry()

    memory = create_memory()

    registry.register(memory)

    assert registry.count() == 1

    loaded = registry.get(memory.memory_id)

    assert loaded.memory_id == memory.memory_id

    assert loaded.learning_id == memory.learning_id


def test_duplicate_registration():

    registry = MemoryRegistry()

    memory = create_memory()

    registry.register(memory)

    try:
        registry.register(memory)
        assert False
    except ValueError:
        assert True
