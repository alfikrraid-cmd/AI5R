from dataclasses import dataclass, field
from datetime import datetime, UTC


@dataclass
class SalesProposal:
    proposal_id: str
    customer_id: str
    opportunity_id: str
    title: str
    problem_statement: str
    proposed_solution: str
    scope: list[str] = field(default_factory=list)
    timeline: str = "To be confirmed"
    investment: float = 0
    currency: str = "IDR"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
