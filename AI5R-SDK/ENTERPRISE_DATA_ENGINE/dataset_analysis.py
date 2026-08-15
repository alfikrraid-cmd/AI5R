from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class WorksheetAnalysis:
    worksheet_name: str
    row_count: int
    column_count: int
    empty_row_count: int
    empty_column_count: int
    cell_statistics: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cell_statistics",
            MappingProxyType(dict(self.cell_statistics)),
        )


@dataclass(frozen=True)
class DatasetAnalysis:
    worksheets: tuple[WorksheetAnalysis, ...]
    worksheet_count: int
    row_count: int
    column_count: int
    empty_row_count: int
    empty_column_count: int
    cell_statistics: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "worksheets", tuple(self.worksheets))
        object.__setattr__(
            self,
            "cell_statistics",
            MappingProxyType(dict(self.cell_statistics)),
        )


__all__ = ["DatasetAnalysis", "WorksheetAnalysis"]
