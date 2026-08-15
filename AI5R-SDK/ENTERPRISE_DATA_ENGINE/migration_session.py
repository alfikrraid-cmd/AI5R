from dataclasses import dataclass

from .column_mapping import DatasetColumnMapping
from .commit_result import CommitResult
from .dataset_analysis import DatasetAnalysis
from .dataset_schema import DatasetSchema
from .detected_enterprise_object import DetectedEnterpriseObjects
from .document_classification import DocumentClassification
from .import_preview import ImportPreview
from .import_result import ImportResult
from .source_descriptor import SourceDescriptor
from .validation_result import ValidationResult


@dataclass(frozen=True)
class MigrationSession:
    source: SourceDescriptor
    import_result: ImportResult
    analysis: DatasetAnalysis
    schemas: tuple[DatasetSchema, ...]
    column_mappings: tuple[DatasetColumnMapping, ...]
    classifications: tuple[DocumentClassification, ...]
    detected_objects: tuple[DetectedEnterpriseObjects, ...]
    validation: ValidationResult
    import_preview: ImportPreview
    commit_result: CommitResult | None
    status: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schemas", tuple(self.schemas))
        object.__setattr__(
            self,
            "column_mappings",
            tuple(self.column_mappings),
        )
        object.__setattr__(
            self,
            "classifications",
            tuple(self.classifications),
        )
        object.__setattr__(
            self,
            "detected_objects",
            tuple(self.detected_objects),
        )


__all__ = ["MigrationSession"]
