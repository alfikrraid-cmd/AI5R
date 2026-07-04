from uuid import uuid4

from .decision_object import DecisionObject


class DecisionEngine:
    """
    Enterprise Brain Stage

    Hypothesis
        ↓
    Decision
    """

    def decide(self, hypothesis):

        if not hypothesis.hypotheses:
            raise ValueError("No hypotheses available")

        selected = max(
            hypothesis.hypotheses,
            key=lambda h: h["confidence"]
        )

        rationale = (
            "Selected because it has the highest confidence among generated hypotheses."
        )

        return DecisionObject(
            decision_id=f"decision-{uuid4()}",
            hypothesis_id=hypothesis.hypothesis_id,
            selected_hypothesis=selected,
            rationale=rationale,
            confidence=selected["confidence"],
            digital_thread_id=hypothesis.digital_thread_id,
            enterprise_context={
                "stage": "decision",
                "derived_from": "hypothesis",
                "candidate_count": len(hypothesis.hypotheses),
            },
        )
