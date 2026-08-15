from dataclasses import dataclass

from .validation_result import ValidationIssue


@dataclass(frozen=True)
class WorksheetPreview:
    worksheet_name: str
    document_type: str
    detected_objects: tuple[str, ...]
    is_valid: bool
    mapped_columns: tuple[int, ...]
    column_count: int
    data_row_count: int
    estimated_imported_objects: int
    error_count: int
    warning_count: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "detected_objects",
            tuple(self.detected_objects),
        )
        object.__setattr__(
            self,
            "mapped_columns",
            tuple(self.mapped_columns),
        )


@dataclass(frozen=True)
class ImportPreview:
    is_valid: bool
    worksheets: tuple[WorksheetPreview, ...]
    total_estimated_objects: int
    errors: tuple[ValidationIssue, ...]
    warnings: tuple[ValidationIssue, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "worksheets", tuple(self.worksheets))
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "warnings", tuple(self.warnings))


__all__ = ["ImportPreview", "WorksheetPreview"]
