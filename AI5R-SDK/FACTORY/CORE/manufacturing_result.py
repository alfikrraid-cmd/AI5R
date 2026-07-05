from dataclasses import dataclass
from typing import Any


@dataclass
class ManufacturingResult:
    status: str
    station: str
    manufactured_object: dict[str, Any]
    object_id: str
    manufactured_at: str
    events: list[dict[str, Any]]
