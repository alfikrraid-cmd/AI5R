from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CapabilityAssignment:
    step: str
    capability: str
    confidence: float = 0.80

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "capability": self.capability,
            "confidence": self.confidence,
        }
