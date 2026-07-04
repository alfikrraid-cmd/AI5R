from uuid import uuid4
from typing import Any, Dict, List

from .understanding_object import UnderstandingObject


class UnderstandingEngine:
    """
    Enterprise Brain stage:
    Observation -> Understanding
    """

    def understand(self, observation: Dict[str, Any]) -> UnderstandingObject:
        if observation.get("object_type") != "observation":
            raise ValueError("Input must be an Observation Object")

        observation_id = observation.get("object_id")
        source_object_id = observation.get("source_object_id")

        if not observation_id:
            raise ValueError("Observation must have object_id")

        if not source_object_id:
            raise ValueError("Observation must have source_object_id")

        facts = observation.get("facts", {})
        signals = observation.get("signals", [])

        return UnderstandingObject(
            understanding_id=f"understanding-{uuid4()}",
            observation_id=observation_id,
            meaning=self._derive_meaning(facts, signals),
            confidence=self._derive_confidence(signals),
            digital_thread_id=source_object_id,
            enterprise_context={
                "source_object_id": source_object_id,
                "stage": "understanding",
                "derived_from": "observation",
                "signals": signals,
            },
        )

    def _derive_meaning(self, facts: Dict[str, Any], signals: List[str]) -> str:
        if signals:
            return "Observation indicates enterprise-relevant signals: " + ", ".join(signals)

        if facts:
            return "Observation contains facts that require enterprise interpretation"

        return "Observation contains no significant enterprise signal"

    def _derive_confidence(self, signals: List[str]) -> float:
        if not signals:
            return 0.3

        critical_signals = [
            signal for signal in signals
            if signal.startswith("high_")
        ]

        if critical_signals:
            return 0.85

        return 0.65
