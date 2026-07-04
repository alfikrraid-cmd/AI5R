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


def test_execution_engine():

    reality = {
        "object_id": "reality-009",
        "object_type": "reality",
        "asset": "pump-009",
        "measurements": {
            "vibration": 14,
            "temperature": 96,
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

    assert execution.status == "ready"

    assert execution.progress == 0.0

    assert len(execution.tasks) == 3

    assert execution.enterprise_context["stage"] == "execution"

    assert execution.digital_thread_id == "reality-009"


def test_execution_object_to_dict():

    reality = {
        "object_id": "reality-010",
        "object_type": "reality",
        "asset": "motor-010",
        "measurements": {
            "vibration": 3,
            "temperature": 55,
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

    data = execution.to_dict()

    assert data["status"] == "ready"

    assert data["progress"] == 0.0

    assert data["enterprise_context"]["derived_from"] == "planning"
