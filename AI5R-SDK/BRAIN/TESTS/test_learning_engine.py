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


def test_learning_engine():

    reality = {
        "object_id": "reality-013",
        "object_type": "reality",
        "asset": "pump-013",
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

    assert learning.status == "learned"

    assert learning.confidence_delta > 0

    assert learning.knowledge_update_required is False

    assert learning.enterprise_context["stage"] == "learning"


def test_learning_object_to_dict():

    reality = {
        "object_id": "reality-014",
        "object_type": "reality",
        "asset": "motor-014",
        "measurements": {
            "vibration": 4,
            "temperature": 60,
        },
        "findings": [],
    }

    observation = ObservationEngine().observe(reality)

    understanding = UnderstandingEngine().understand(observation)

    hypothesis = HypothesisEngine().hypothesize(understanding)

    decision = DecisionEngine().decide(hypothesis)

    planning = PlanningEngine().process(decision)

    execution = ExecutionEngine().process(planning)

    outcome = OutcomeEngine().process(execution)

    learning = LearningEngine().process(outcome)

    data = learning.to_dict()

    assert data["status"] == "learned"

    assert data["enterprise_context"]["derived_from"] == "outcome"

    assert data["confidence_delta"] > 0
