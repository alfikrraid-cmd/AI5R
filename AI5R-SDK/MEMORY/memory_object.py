from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, Any


@dataclass
class MemoryObject:
    """
    Canonical Enterprise Memory Object.

    Memory is produced from Learning and becomes
    the persistent enterprise memory layer.
    """

    memory_id: str

    learning_id: str

    memory_type: str = "enterprise_memory"

    content: Dict[str, Any] = field(default_factory=dict)

    confidence: float = 0.0

    digital_thread_id: str = ""

    status: str = "memorized"

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_dict(self):

        return {

            "memory_id": self.memory_id,

            "learning_id": self.learning_id,

            "memory_type": self.memory_type,

            "content": self.content,

            "confidence": self.confidence,

            "digital_thread_id": self.digital_thread_id,

            "status": self.status,

            "created_at": self.created_at,
        }
