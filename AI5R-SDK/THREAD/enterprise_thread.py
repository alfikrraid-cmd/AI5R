from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4


@dataclass
class EnterpriseThread:
    """
    Enterprise Cognitive Thread

    Carries enterprise work through AI5R canonical stations.
    """

    organization_id: str
    mission_id: str
    thread_name: str

    worker_id: str | None = None
    digital_thread_id: str | None = None

    current_station: str = "MISSION"
    status: str = "ACTIVE"

    station_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    object_type: str = "ENTERPRISE_THREAD"
    thread_id: str = field(default_factory=lambda: str(uuid4()))

    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def move_to(self, station: str):
        self.station_history.append({
            "from": self.current_station,
            "to": station,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.current_station = station
        self.updated_at = datetime.utcnow().isoformat()
        return self

    def close(self):
        self.status = "CLOSED"
        self.updated_at = datetime.utcnow().isoformat()
        return self

    def to_dict(self):
        return self.__dict__
