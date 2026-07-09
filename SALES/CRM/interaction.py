from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass
class CustomerInteraction:
    interaction_id: str
    customer_id: str
    interaction_type: str
    notes: str
    created_at: str = ""
    next_followup_at: str | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()
