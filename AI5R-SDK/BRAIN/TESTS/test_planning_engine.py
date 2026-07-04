import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.observation_engine import ObservationEngine
from BRAIN.understanding_engine import UnderstandingEngine
from BRAIN.hypothesis_engine import HypothesisEngine
from BRAIN.decision_engine import DecisionEngine
from BRAIN.planning_engine import PlanningEngine


def test_planning_engine():

    reality = {
        "object_id": "reality-007",
        "object_type": "reality",
        "asset": "pump-007",
        "measurements": {
            "vibration": 15,
            "temperature": 100,
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

    plan = PlanningEngine().process(
        decision
    )

    assert plan.status == "planned"

    assert plan.estimated_steps == 3

    assert len(plan.actions) == 3

    assert plan.enterprise_context["stage"] == "planning"

    assert plan.digital_thread_id == "reality-007"


def test_planning_object_to_dict():

    reality = {
        "object_id": "reality-008",
        "object_type": "reality",
        "asset": "motor-001",
        "measurements": {
            "vibration": 5,
            "temperature": 60,
        },
        "findings": [],
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

    plan = PlanningEngine().process(
        decision
    )

    data = plan.to_dict()

    assert data["status"] == "planned"

    assert data["estimated_steps"] == 3

    assert data["enterprise_context"]["derived_from"] == "decision"
