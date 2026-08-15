from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedEnterpriseObject:
    object_type: str
    role: str
    confidence: float
    source_columns: tuple[int, ...]
    document_type: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_columns", tuple(self.source_columns))


@dataclass(frozen=True)
class DetectedEnterpriseObjects:
    worksheet_name: str
    document_type: str
    primary_object: DetectedEnterpriseObject
    related_objects: tuple[DetectedEnterpriseObject, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "related_objects", tuple(self.related_objects))


__all__ = ["DetectedEnterpriseObject", "DetectedEnterpriseObjects"]
