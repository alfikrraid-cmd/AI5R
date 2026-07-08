from dataclasses import dataclass


@dataclass(slots=True)
class FinanceIntent:
    intent: str
    amount: int
    category: str
    payment_channel: str | None = None
    company: str | None = None
    project: str | None = None
    raw_text: str = ""
    confidence: float = 0.0
