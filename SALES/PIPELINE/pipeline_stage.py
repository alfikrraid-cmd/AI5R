from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineStage:
    code: str
    name: str
    probability: float
    order: int
    is_closed: bool = False


NEW_LEAD = PipelineStage("NEW_LEAD", "New Lead", 0.05, 1)
QUALIFIED = PipelineStage("QUALIFIED", "Qualified", 0.20, 2)
DISCOVERY = PipelineStage("DISCOVERY", "Discovery", 0.40, 3)
PROPOSAL = PipelineStage("PROPOSAL", "Proposal", 0.60, 4)
NEGOTIATION = PipelineStage("NEGOTIATION", "Negotiation", 0.80, 5)
WON = PipelineStage("WON", "Won", 1.00, 6, True)
LOST = PipelineStage("LOST", "Lost", 0.00, 6, True)
