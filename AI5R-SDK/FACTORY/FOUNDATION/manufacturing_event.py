from dataclasses import dataclass, field
from datetime import datetime, UTC


@dataclass
class ManufacturingEvent:
    """
    Canonical manufacturing event.
    """

    event_type: str

    station: str

    build_id: str

    product: str

    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    payload: dict = field(default_factory=dict)

    def to_dict(self):

        return {
            "event_type": self.event_type,
            "station": self.station,
            "build_id": self.build_id,
            "product": self.product,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }
