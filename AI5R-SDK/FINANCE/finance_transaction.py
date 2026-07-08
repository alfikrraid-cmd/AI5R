from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class FinanceTransaction:
    transaction_id: str
    intent: str
    amount: int
    category: str
    company: str | None = None
    project: str | None = None
    payment_channel: str | None = None
    status: str = "DRAFT"
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
