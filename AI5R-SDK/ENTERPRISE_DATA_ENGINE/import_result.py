from dataclasses import dataclass

from .raw_dataset import RawDataset
from .source_descriptor import SourceDescriptor


@dataclass(frozen=True)
class ImportResult:
    source: SourceDescriptor
    reader_name: str
    dataset: RawDataset
    success: bool = True


__all__ = ["ImportResult"]