from dataclasses import dataclass, field
from typing import Any


@dataclass
class SalesTarget:
    revenue_target: float
    period: str = "monthly"
    currency: str = "IDR"


@dataclass
class SalesPlan:
    target: SalesTarget
    required_leads: int
    required_closings: int
    conversion_rate: float
    actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
