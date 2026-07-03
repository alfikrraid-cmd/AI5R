"""
AI5R Enterprise Event Contract
EL-004

Defines the common event contract for all AI5R Enterprise activities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4


@dataclass
class EnterpriseEvent:
    event_type: str
    source: str
    payload: Dict[str, Any] = field(default_factory=dict)
    target: Optional[str] = None
    mission_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "target": self.target,
            "mission_id": self.mission_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "metadata": self.metadata,
        }
