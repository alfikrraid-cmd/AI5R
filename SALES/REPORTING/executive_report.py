from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutiveReport:
    executive: str
    goal: str
    summary: str
    kpis: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
