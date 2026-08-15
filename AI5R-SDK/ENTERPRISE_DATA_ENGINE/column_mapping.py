from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ColumnMapping:
    column_index: int
    source_header: Any
    semantic_label: str
    confidence: float


@dataclass(frozen=True)
class DatasetColumnMapping:
    worksheet_name: str
    mappings: tuple[ColumnMapping, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "mappings", tuple(self.mappings))


__all__ = ["ColumnMapping", "DatasetColumnMapping"]
