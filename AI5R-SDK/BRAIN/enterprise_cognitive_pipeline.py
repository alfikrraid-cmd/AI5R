from .observation_engine import ObservationEngine
from .understanding_engine import UnderstandingEngine
from .hypothesis_engine import HypothesisEngine
from .decision_engine import DecisionEngine
from .planning_engine import PlanningEngine
from .execution_engine import ExecutionEngine
from .outcome_engine import OutcomeEngine
from .learning_engine import LearningEngine


class EnterpriseCognitivePipeline:
    """
    End-to-end Enterprise Cognitive Thread.

    Reality
        -> Observation
        -> Understanding
        -> Hypothesis
        -> Decision
        -> Planning
        -> Execution
        -> Outcome
        -> Learning
    """

    def __init__(self):
        self.observation_engine = ObservationEngine()
        self.understanding_engine = UnderstandingEngine()
        self.hypothesis_engine = HypothesisEngine()
        self.decision_engine = DecisionEngine()
        self.planning_engine = PlanningEngine()
        self.execution_engine = ExecutionEngine()
        self.outcome_engine = OutcomeEngine()
        self.learning_engine = LearningEngine()

    def run(self, reality):
        observation = self.observation_engine.observe(reality)
        understanding = self.understanding_engine.understand(observation)
        hypothesis = self.hypothesis_engine.hypothesize(understanding)
        decision = self.decision_engine.decide(hypothesis)
        planning = self.planning_engine.process(decision)
        execution = self.execution_engine.process(planning)
        outcome = self.outcome_engine.process(execution)
        learning = self.learning_engine.process(outcome)

        return {
            "reality": reality,
            "observation": observation,
            "understanding": understanding,
            "hypothesis": hypothesis,
            "decision": decision,
            "planning": planning,
            "execution": execution,
            "outcome": outcome,
            "learning": learning,
        }
