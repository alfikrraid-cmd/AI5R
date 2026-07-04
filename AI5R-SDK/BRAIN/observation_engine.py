from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class ObservationObject:
    object_id: str
    object_type: str = "observation"
    source_object_id: str = ""
    facts: Dict[str, Any] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)
    status: str = "observed"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "source_object_id": self.source_object_id,
            "facts": self.facts,
            "signals": self.signals,
            "status": self.status,
            "created_at": self.created_at,
        }


class ObservationEngine:
    def observe(self, reality: Dict[str, Any]) -> Dict[str, Any]:
        if reality.get("object_type") != "reality":
            raise ValueError("Input must be a Reality Object")

        facts = {}

        if reality.get("asset"):
            facts["asset"] = reality.get("asset")

        if reality.get("measurements"):
            facts["measurements"] = reality.get("measurements")

        if reality.get("findings"):
            facts["findings"] = reality.get("findings")

        signals = self._derive_signals(facts)

        observation = ObservationObject(
            object_id=f"obs-{reality.get('object_id', 'unknown')}",
            source_object_id=reality.get("object_id", ""),
            facts=facts,
            signals=signals,
        )

        return observation.to_dict()

    def _derive_signals(self, facts: Dict[str, Any]) -> List[str]:
        signals = []

        measurements = facts.get("measurements", {})
        findings = facts.get("findings", [])

        vibration = measurements.get("vibration")
        temperature = measurements.get("temperature")

        if vibration is not None:
            signals.append("vibration_observed")
            if vibration >= 10:
                signals.append("high_vibration_observed")

        if temperature is not None:
            signals.append("temperature_observed")
            if temperature >= 90:
                signals.append("high_temperature_observed")

        for finding in findings:
            signals.append(f"{finding}_observed")

        return list(dict.fromkeys(signals))
