from datetime import datetime, timezone
from uuid import uuid4
import json


class EnterpriseCognitiveContext:
    COGNITIVE_FIELDS = [
        "reality",
        "warehouse",
        "experience",
        "memory",
        "knowledge",
        "capability",
        "recommendation",
        "decision",
        "plan",
        "execution",
        "learning",
    ]

    def __init__(self, mission_id=None, trace_id=None, metadata=None):
        self.trace_id = trace_id or str(uuid4())
        self.mission_id = mission_id
        self.metadata = metadata or {}
        self.history = []

        for field in self.COGNITIVE_FIELDS:
            setattr(self, field, None)

        self.record_history("context_created")

    def record_history(self, action, data=None):
        self.history.append(
            {
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data or {},
            }
        )

    def set(self, field, value):
        if field not in self.COGNITIVE_FIELDS:
            raise ValueError(f"Unknown cognitive field: {field}")

        setattr(self, field, value)
        self.record_history(f"{field}_set", {"field": field})
        return self

    def get(self, field):
        if field not in self.COGNITIVE_FIELDS:
            raise ValueError(f"Unknown cognitive field: {field}")

        return getattr(self, field)

    def merge(self, other):
        if self.trace_id != other.trace_id:
            raise ValueError("Cannot merge contexts with different trace_id")

        for field in self.COGNITIVE_FIELDS:
            current_value = getattr(self, field)
            other_value = getattr(other, field)

            if current_value is None and other_value is not None:
                setattr(self, field, other_value)
                self.record_history(
                    "field_merged",
                    {"field": field},
                )

        self.history.extend(other.history)
        self.record_history("context_merged")

        return self

    def to_dict(self):
        return {
            "trace_id": self.trace_id,
            "mission_id": self.mission_id,
            "metadata": self.metadata,
            "history": self.history,
            **{
                field: self._serialize(getattr(self, field))
                for field in self.COGNITIVE_FIELDS
            },
        }

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def _serialize(self, value):
        if value is None:
            return None

        if hasattr(value, "to_dict"):
            return value.to_dict()

        return value
