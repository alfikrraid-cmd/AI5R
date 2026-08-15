from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ColumnSchema:
    column_index: int
    header: Any
    dominant_data_type: str
    populated_count: int
    empty_count: int


@dataclass(frozen=True)
class DatasetSchema:
    worksheet_name: str
    header_row: int | None
    data_region: tuple[int, int] | None
    column_count: int
    columns: tuple[ColumnSchema, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "columns", tuple(self.columns))


__all__ = ["ColumnSchema", "DatasetSchema"]
