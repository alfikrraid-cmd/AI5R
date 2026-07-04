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


def test_outcome_engine():

    reality = {
        "object_id": "reality-011",
        "object_type": "reality",
        "asset": "pump-011",
        "measurements": {
            "vibration": 15,
            "temperature": 100,
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

    assert outcome.status == "completed"

    assert outcome.success is True

    assert outcome.completion_rate == 1.0

    assert len(outcome.completed_tasks) == 3

    assert outcome.enterprise_context["stage"] == "outcome"


def test_outcome_object_to_dict():

    reality = {
        "object_id": "reality-012",
        "object_type": "reality",
        "asset": "motor-012",
        "measurements": {
            "vibration": 4,
            "temperature": 65,
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

    data = outcome.to_dict()

    assert data["status"] == "completed"

    assert data["success"] is True

    assert data["completion_rate"] == 1.0

    assert data["enterprise_context"]["derived_from"] == "execution"
