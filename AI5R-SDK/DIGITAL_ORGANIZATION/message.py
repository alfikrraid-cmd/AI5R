from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Message:
    sender: str
    receiver: str
    content: str
    message_type: str = "TASK"
    status: str = "SENT"
    message_id: str = field(default_factory=lambda: f"MSG-{uuid4()}")
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
