from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProductionLine:
    line_id: str
    line_name: str
    product_type: str
    station_ids: tuple[str, ...] = ()
    capability_ids: tuple[str, ...] = ()
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)
    canonical_base: str = "ManufacturingObject"

    def validate(self) -> bool:
        return bool(
            self.line_id
            and self.line_name
            and self.product_type
            and len(self.execution_ids()) > 0
        )

    def execution_ids(self) -> tuple[str, ...]:
        if self.capability_ids:
            return self.capability_ids
        return self.station_ids

    def station_count(self) -> int:
        return len(self.station_ids)

    def capability_count(self) -> int:
        return len(self.capability_ids)

    def execution_count(self) -> int:
        return len(self.execution_ids())

    def is_capability_based(self) -> bool:
        return bool(self.capability_ids)
