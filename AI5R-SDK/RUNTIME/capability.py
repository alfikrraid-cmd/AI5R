from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RuntimeCapability:
    capability_id: str
    capability_name: str
    version: str = "1.0.0"
    input_contract: dict[str, Any] = field(default_factory=dict)
    output_contract: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        return bool(
            self.capability_id
            and self.capability_name
            and self.version
        )

    def qualified_id(self) -> str:
        return f"{self.capability_id}@{self.version}"
