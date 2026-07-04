from uuid import uuid4
from typing import Any, Dict, List

from .hypothesis_object import HypothesisObject


class HypothesisEngine:
    """
    Enterprise Brain stage:
    Understanding -> Hypothesis
    """

    def hypothesize(self, understanding: Any) -> HypothesisObject:
        understanding_id = getattr(understanding, "understanding_id", None)
        digital_thread_id = getattr(understanding, "digital_thread_id", "")

        if not understanding_id:
            raise ValueError("Understanding must have understanding_id")

        signals = getattr(understanding, "enterprise_context", {}).get("signals", [])
        meaning = getattr(understanding, "meaning", "")

        hypotheses = self._derive_hypotheses(signals, meaning)

        return HypothesisObject(
            hypothesis_id=f"hypothesis-{uuid4()}",
            understanding_id=understanding_id,
            hypotheses=hypotheses,
            selected=False,
            digital_thread_id=digital_thread_id,
            enterprise_context={
                "stage": "hypothesis",
                "derived_from": "understanding",
                "signal_count": len(signals),
            },
        )

    def _derive_hypotheses(
        self,
        signals: List[str],
        meaning: str,
    ) -> List[Dict[str, Any]]:
        hypotheses = []

        if "high_vibration_observed" in signals:
            hypotheses.append({
                "name": "mechanical_instability",
                "description": "High vibration may indicate imbalance, misalignment, or bearing wear.",
                "confidence": 0.82,
            })

        if "high_temperature_observed" in signals:
            hypotheses.append({
                "name": "thermal_stress",
                "description": "High temperature may indicate overload, friction, or cooling degradation.",
                "confidence": 0.78,
            })

        if any("leak" in signal for signal in signals):
            hypotheses.append({
                "name": "seal_or_fluid_integrity_issue",
                "description": "Leak-related signals may indicate seal degradation or fluid containment failure.",
                "confidence": 0.74,
            })

        if not hypotheses:
            hypotheses.append({
                "name": "general_enterprise_signal",
                "description": meaning or "Understanding indicates a signal requiring further enterprise analysis.",
                "confidence": 0.5,
            })

        return hypotheses
