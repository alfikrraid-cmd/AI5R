import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.enterprise_brain_registry import EnterpriseBrainRegistry
from BRAIN.observation_engine import ObservationEngine
from BRAIN.understanding_engine import UnderstandingEngine
from BRAIN.hypothesis_engine import HypothesisEngine
from BRAIN.decision_engine import DecisionEngine
from BRAIN.planning_engine import PlanningEngine
from BRAIN.execution_engine import ExecutionEngine
from BRAIN.outcome_engine import OutcomeEngine
from BRAIN.learning_engine import LearningEngine


def test_registry_registers_all_stages():

    registry = EnterpriseBrainRegistry()

    registry.register("observation", ObservationEngine())
    registry.register("understanding", UnderstandingEngine())
    registry.register("hypothesis", HypothesisEngine())
    registry.register("decision", DecisionEngine())
    registry.register("planning", PlanningEngine())
    registry.register("execution", ExecutionEngine())
    registry.register("outcome", OutcomeEngine())
    registry.register("learning", LearningEngine())

    assert registry.count() == 8

    assert registry.get("decision").__class__.__name__ == "DecisionEngine"

    assert registry.get("learning").__class__.__name__ == "LearningEngine"


def test_registry_prevents_duplicate_registration():

    registry = EnterpriseBrainRegistry()

    registry.register("observation", ObservationEngine())

    try:
        registry.register("observation", ObservationEngine())
        assert False
    except ValueError:
        assert True
