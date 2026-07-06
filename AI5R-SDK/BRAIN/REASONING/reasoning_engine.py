from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Decision:
    input: Any
    reasoning: str
    output: Any
    confidence: float


class ReasoningEngine:
    def __init__(self):
        self.history: list[Decision] = []

    def think(self, input_data: Any) -> Decision:
        # simple deterministic reasoning layer (placeholder for future AI)
        if isinstance(input_data, dict) and input_data.get("risk") == "high":
            output = "REJECT"
            reasoning = "High risk detected, system safety rule applied"
            confidence = 0.95
        else:
            output = "APPROVE"
            reasoning = "No risk detected, safe to proceed"
            confidence = 0.80

        decision = Decision(
            input=input_data,
            reasoning=reasoning,
            output=output,
            confidence=confidence,
        )

        self.history.append(decision)
        return decision

    def snapshot(self):
        return [
            {
                "input": d.input,
                "output": d.output,
                "confidence": d.confidence,
            }
            for d in self.history
        ]
