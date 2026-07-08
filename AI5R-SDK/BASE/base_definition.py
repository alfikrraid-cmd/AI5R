from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BaseDefinition:
    definition_id: str
    definition_name: str
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate_base(self) -> bool:
        return bool(
            self.definition_id
            and self.definition_name
            and self.version
        )
