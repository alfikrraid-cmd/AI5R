from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EmployeeAssignment:
    step: str
    capability: str
    employee_id: str
    employee_role: str
    confidence: float = 0.85

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "capability": self.capability,
            "employee_id": self.employee_id,
            "employee_role": self.employee_role,
            "confidence": self.confidence,
        }
