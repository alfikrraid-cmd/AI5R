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


def test_memory_engine():

    reality = {
        "object_id": "reality-101",
        "object_type": "reality",
        "asset": "pump-101",
        "measurements": {
            "vibration": 15,
            "temperature": 95,
        },
        "findings": [
            "leak",
        ],
    }

    observation = ObservationEngine().observe(reality)

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

    learning = LearningEngine().process(
        outcome
    )

    memory = MemoryEngine().memorize(
        learning
    )

    assert memory.status == "memorized"

    assert memory.learning_id == learning.learning_id

    assert memory.content["lesson"] == learning.lesson

    assert memory.digital_thread_id == "reality-101"


def test_memory_to_dict():

    reality = {
        "object_id": "reality-102",
        "object_type": "reality",
        "asset": "motor-102",
        "measurements": {
            "vibration": 4,
            "temperature": 60,
        },
        "findings": [],
    }

    observation = ObservationEngine().observe(reality)

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

    learning = LearningEngine().process(
        outcome
    )

    memory = MemoryEngine().memorize(
        learning
    )

    data = memory.to_dict()

    assert data["status"] == "memorized"

    assert data["learning_id"] == learning.learning_id
